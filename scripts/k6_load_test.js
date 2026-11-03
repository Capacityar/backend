/**
 * CapacityAR — k6 Load Testing Script ([S6.6][E1+E2])
 *
 * Evalúa la capacidad, latencia (P50/P95/P99) y tasa de errores bajo carga
 * en los endpoints críticos del backend con PLAN_GENERATOR=mock:
 *   1. POST /api/learning-paths
 *   2. GET  /api/learning-paths/{id}
 *   3. POST /api/attempts
 *
 * Ejecución:
 *   k6 run -e BASE_URL=http://localhost:8000 scripts/k6_load_test.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Trend, Rate } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const postLearningPathDuration = new Trend("post_learning_path_duration", true);
const getLearningPathDuration = new Trend("get_learning_path_duration", true);
const postAttemptDuration = new Trend("post_attempt_duration", true);
const workflowSuccessRate = new Rate("workflow_success_rate");

export const options = {
  stages: [
    { duration: "10s", target: 1 },  // Línea base (1 VU)
    { duration: "15s", target: 5 },  // Carga baja (5 VUs)
    { duration: "20s", target: 10 }, // Carga moderada (10 VUs)
    { duration: "20s", target: 25 }, // Pico de estrés (25 VUs)
    { duration: "10s", target: 0 },  // Enfriamiento
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],          // < 1% de fallos permitidos
    http_req_duration: ["p(95)<2500"],       // P95 < 2.5s en modo mock (< 10s presupuesto global)
    post_learning_path_duration: ["p(95)<2500"],
    get_learning_path_duration: ["p(95)<1000"],
    post_attempt_duration: ["p(95)<2500"],
    workflow_success_rate: ["rate>0.99"],
  },
};

function buildGapReportPayload(studentEmail) {
  return JSON.stringify({
    student: {
      name: "Ana Perez",
      email: studentEmail,
      skills: [
        { name: "Git", level: 1 },
        { name: "SQL", level: 2 },
      ],
      interests: ["backend", "logistica"],
    },
    company: { name: "Empresa Logistica SA" },
    target_role: {
      title: "Backend Developer Junior",
      required_skills: [
        { name: "Git", level: 3, priority: "HIGH" },
        { name: "SQL", level: 3, priority: "HIGH" },
      ],
    },
    summary: "Ana necesita reforzar Git y SQL.",
    readiness_score: 45,
    skills: [
      {
        name: "Git",
        current_level: 1,
        required_level: 3,
        gap_level: 2,
        priority: "HIGH",
        status: "MISSING",
      },
      {
        name: "SQL",
        current_level: 2,
        required_level: 3,
        gap_level: 1,
        priority: "HIGH",
        status: "NEEDS_WORK",
      },
    ],
  });
}

export default function () {
  const uniqueEmail = `student_vu${__VU}_iter${__ITER}@example.com`;
  const headers = { "Content-Type": "application/json" };

  // 1. POST /api/learning-paths
  const createRes = http.post(
    `${BASE_URL}/api/learning-paths`,
    buildGapReportPayload(uniqueEmail),
    { headers, tags: { endpoint: "POST /api/learning-paths" } }
  );
  postLearningPathDuration.add(createRes.timings.duration);

  const createdOk = check(createRes, {
    "POST /api/learning-paths status is 201": (r) => r.status === 201,
    "POST /api/learning-paths has id": (r) => {
      try {
        return JSON.parse(r.body).id > 0;
      } catch (_) {
        return false;
      }
    },
  });

  if (!createdOk) {
    workflowSuccessRate.add(false);
    return;
  }

  const pathId = JSON.parse(createRes.body).id;

  // 2. GET /api/learning-paths/{id}
  const getRes = http.get(`${BASE_URL}/api/learning-paths/${pathId}`, {
    tags: { endpoint: "GET /api/learning-paths/{id}" },
  });
  getLearningPathDuration.add(getRes.timings.duration);

  const getOk = check(getRes, {
    "GET /api/learning-paths/{id} status is 200": (r) => r.status === 200,
  });

  // 3. POST /api/attempts
  const attemptPayload = JSON.stringify({
    student_email: uniqueEmail,
    learning_path_id: pathId,
    module_index: 0,
    unit_index: 2,
    exercise_index: 0,
    answer: "respuesta de ejemplo",
    time_spent_seconds: 30,
  });

  const attemptRes = http.post(
    `${BASE_URL}/api/attempts`,
    attemptPayload,
    { headers, tags: { endpoint: "POST /api/attempts" } }
  );
  postAttemptDuration.add(attemptRes.timings.duration);

  const attemptOk = check(attemptRes, {
    "POST /api/attempts status is 201": (r) => r.status === 201,
    "POST /api/attempts evaluated is_correct": (r) => {
      try {
        return typeof JSON.parse(r.body).is_correct === "boolean";
      } catch (_) {
        return false;
      }
    },
  });

  workflowSuccessRate.add(createdOk && getOk && attemptOk);
  sleep(0.1);
}
