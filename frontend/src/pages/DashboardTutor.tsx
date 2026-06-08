import React, { useState } from "react";
import { AppLayout } from "@/components/AppLayout";
import { AlertTriangle, CheckCircle, Clock, UserX, Award, Briefcase } from "lucide-react";
import { 
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from "recharts";
import { Link } from "wouter";


// JSON 
const datosRubros = {
  comercio: {
    nombre: "Comercio y Servicios",
    riesgo_abandono: "12%",
    evaluaciones_criticas: "8 casos activos",
    tasa_completitud: "78%",
    tiempo_dominio_80: "4.2 semanas",
    tasa_desercion: "5.4%",
    readiness_final: "Intermedio-Alto",
    insercion_laboral: "82%",
    historicoCohortes: [
      { name: "C1-25", completitud: 70, desercion: 8 },
      { name: "C2-25", completitud: 74, desercion: 6 },
      { name: "C1-26", completitud: 78, desercion: 5.4 }
    ],
    distribucionReadiness: [
      { nivel: "Inicial", alumnos: 15 },
      { nivel: "Intermedio", alumnos: 45 },
      { nivel: "Avanzado", alumnos: 30 },
      { nivel: "Tech Ready", alumnos: 12 }
    ],
    historicoInsercion: [
      { anio: "2024", tasa: 75 },
      { anio: "2025", tasa: 79 },
      { anio: "2026", tasa: 82 }
    ]
  },
  industria: {
    nombre: "Industria y Metalmecánica",
    riesgo_abandono: "24%",
    evaluaciones_criticas: "15 casos activos",
    tasa_completitud: "61%",
    tiempo_dominio_80: "6.8 semanas",
    tasa_desercion: "11.2%",
    readiness_final: "Junior Técnico",
    insercion_laboral: "74%",
    historicoCohortes: [
      { name: "C1-25", completitud: 55, desercion: 14 },
      { name: "C2-25", completitud: 58, desercion: 13 },
      { name: "C1-26", completitud: 61, desercion: 11.2 }
    ],
    distribucionReadiness: [
      { nivel: "Inicial", alumnos: 35 },
      { nivel: "Intermedio", alumnos: 50 },
      { nivel: "Avanzado", alumnos: 20 },
      { nivel: "Tech Ready", alumnos: 5 }
    ],
    historicoInsercion: [
      { anio: "2024", tasa: 68 },
      { anio: "2025", tasa: 70 },
      { anio: "2026", tasa: 74 }
    ]
  },
  software: {
    nombre: "Software y Tecnología (CAME TIC)",
    riesgo_abandono: "8%",
    evaluaciones_criticas: "3 casos activos",
    tasa_completitud: "89%",
    tiempo_dominio_80: "3.5 semanas",
    tasa_desercion: "2.1%",
    readiness_final: "Tech Ready (Apto)",
    insercion_laboral: "91%",
    historicoCohortes: [
      { name: "C1-25", completitud: 82, desercion: 4 },
      { name: "C2-25", completitud: 85, desercion: 3 },
      { name: "C1-26", completitud: 89, desercion: 2.1 }
    ],
    distribucionReadiness: [
      { nivel: "Inicial", alumnos: 8 },
      { nivel: "Intermedio", alumnos: 22 },
      { nivel: "Avanzado", alumnos: 55 },
      { nivel: "Tech Ready", alumnos: 60 }
    ],
    historicoInsercion: [
      { anio: "2024", tasa: 85 },
      { anio: "2025", tasa: 88 },
      { anio: "2026", tasa: 91 }
    ]
  }
};

type RubroKey = keyof typeof datosRubros;

export default function DashboardTutor() {
  const [rubroSeleccionado, setRubroSeleccionado] = useState<RubroKey>("comercio");
  const datos = datosRubros[rubroSeleccionado];

  return (
    <AppLayout activePage="Métricas CAME" userRole="tutor">
      <div className="space-y-6 p-6 max-w-7xl mx-auto">
        
        {/* Encabezado y Selector */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Panel Global del Tutor</h1>
            <p className="text-sm text-slate-500">Monitoreo de métricas adaptativas por sector productivo de CAME</p>
          </div>
          
          <div className="flex items-center gap-3">
            <label htmlFor="rubro" className="text-sm font-semibold text-slate-600 whitespace-nowrap">
              Seleccionar Rubro:
            </label>
            <select
              id="rubro"
              value={rubroSeleccionado}
              onChange={(e) => setRubroSeleccionado(e.target.value as RubroKey)}
              className="bg-slate-50 border border-slate-200 text-slate-700 py-2 px-4 rounded-xl font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all cursor-pointer"
            >
              <option value="comercio"> Comercio y Servicios</option>
              <option value="industria"> Industria y Metalmecánica</option>
              <option value="software"> Software y Tecnología (CAME TIC)</option>
            </select>
          </div>
        </div>


        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
   
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-start gap-4">
            <div className="p-3 bg-red-50 text-red-600 rounded-xl">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Riesgo de Abandono</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{datos.riesgo_abandono}</h3>
              <p className="text-xs text-red-500 font-medium mt-1">⚠️ {datos.evaluaciones_criticas}</p>
            </div>
          </div>

   
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-start gap-4">
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
              <CheckCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Completitud de Path (Cohorte)</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{datos.tasa_completitud}</h3>
              <p className="text-xs text-slate-500 mt-1">Promedio de avance curricular</p>
            </div>
          </div>

  
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-start gap-4">
            <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
              <Clock className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Tiempo hasta Dominio (80%)</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{datos.tiempo_dominio_80}</h3>
              <p className="text-xs text-slate-500 mt-1">Hito de competencia alcanzado</p>
            </div>
          </div>

     
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-start gap-4">
            <div className="p-3 bg-amber-50 text-amber-600 rounded-xl">
              <UserX className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Tasa de Deserción Efectiva</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{datos.tasa_desercion}</h3>
              <p className="text-xs text-slate-500 mt-1">Bajas consolidadas del periodo</p>
            </div>
          </div>

   
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-start gap-4">
            <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Distribución de Readiness</p>
              <h3 className="text-xl font-bold text-slate-800 mt-1 truncate max-w-[200px]">{datos.readiness_final}</h3>
              <p className="text-xs text-slate-500 mt-1">Nivel promedio de salida adaptativa</p>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-start gap-4">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
              <Briefcase className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Tasa de Inserción Laboral</p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{datos.insercion_laboral}</h3>
              <p className="text-xs text-indigo-500 font-medium mt-1">Métrica a largo plazo (Alumnos colocados)</p>
            </div>
          </div>
        </div>

  
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          

          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h3 className="text-base font-bold text-slate-700 mb-4">Evolución Curricular por Cohorte (%)</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={datos.historicoCohortes} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="name" stroke="#94A3B8" fontSize={12} />
                  <YAxis stroke="#94A3B8" fontSize={12} domain={[0, 100]} />
                  <Tooltip />
                  <Legend fontSize={12} />
                  <Line type="monotone" dataKey="completitud" name="Tasa Completitud" stroke="#10B981" strokeWidth={3} activeDot={{ r: 8 }} />
                  <Line type="monotone" dataKey="desercion" name="Tasa Deserción" stroke="#EF4444" strokeWidth={2} strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

  
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <h3 className="text-base font-bold text-slate-700 mb-4">Distribución de Nivel de Salida (Alumnos)</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={datos.distribucionReadiness} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="nivel" stroke="#94A3B8" fontSize={12} />
                  <YAxis stroke="#94A3B8" fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="alumnos" name="Cantidad Alumnos" fill="#8B5CF6" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

     
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 lg:col-span-2">
            <h3 className="text-base font-bold text-slate-700 mb-4">Evolución Histórica de Inserción Laboral (%)</h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={datos.historicoInsercion} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="anio" stroke="#94A3B8" fontSize={12} />
                  <YAxis stroke="#94A3B8" fontSize={12} domain={[0, 100]} />
                  <Tooltip />
                  <Area type="monotone" dataKey="tasa" name="Tasa de Éxito" stroke="#4F46E5" fill="#EEF2FF" strokeWidth={3} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

      </div>
    </AppLayout>
  );
}