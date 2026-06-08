import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { DemoApi } from "@/pages/DemoApi";
import { Dashboard } from "@/pages/Dashboard";
import { PlanCapacitacion } from "@/pages/PlanCapacitacion";
import { ModuloIA } from "@/pages/ModuloIA";
import { Evaluacion } from "@/pages/Evaluacion";
import { ProgresoyLogros } from "@/pages/ProgresoyLogros";
import { CanalTutor } from "@/pages/CanalTutor";
import { PanelTutor } from "@/pages/PanelTutor";
import { DetalleCandidato } from "@/pages/DetalleCandidato";
import DashboardTutor from "@/pages/DashboardTutor";

const queryClient = new QueryClient();

function Router() {
  return (
    <Switch>
      <Route path="/" component={Dashboard} />
      <Route path="/plan" component={PlanCapacitacion} />
      <Route path="/modulo" component={ModuloIA} />
      <Route path="/evaluacion" component={Evaluacion} />
      <Route path="/progreso" component={ProgresoyLogros} />
      <Route path="/canal-tutor" component={CanalTutor} />
      <Route path="/panel-tutor" component={PanelTutor} />
      <Route path="/detalle-candidato" component={DetalleCandidato} />
      <Route path="/dashboard-tutor" component={DashboardTutor} />
      <Route path="/demo-api" component={DemoApi} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
