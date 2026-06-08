import React from "react";
import { useLocation, Link } from "wouter";
import { Bell, Home, BookOpen, GraduationCap, LineChart, MessageSquare, Users, AlertCircle, FileText,BarChart3 } from "lucide-react";

interface AppLayoutProps {
  children: React.ReactNode;
  activePage: string;
  userRole?: "candidato" | "tutor";
  userName?: string;
}

export function AppLayout({ children, activePage, userRole = "candidato", userName = "Lucía Ramírez" }: AppLayoutProps) {
  const isCandidato = userRole === "candidato";

  const candidatoLinks = [
    { name: "Inicio", path: "/", icon: Home },
    { name: "Mi Plan", path: "/plan", icon: BookOpen },
    { name: "Capacitación", path: "/modulo", icon: GraduationCap },
    { name: "Progreso", path: "/progreso", icon: LineChart },
    { name: "Mi Tutor", path: "/canal-tutor", icon: MessageSquare },
  ];

  const tutorLinks = [
    { name: "Mis Candidatos", path: "/panel-tutor", icon: Users },
    { name: "Alertas", path: "/panel-tutor", icon: AlertCircle },
    { name: "Reportes", path: "/panel-tutor", icon: FileText },
    { name: "Métricas CAME", path: "/dashboard-tutor", icon: BarChart3 },
  ];

  const links = isCandidato ? candidatoLinks : tutorLinks;

  const initials = userName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .substring(0, 2)
    .toUpperCase();

  return (
    <div className="flex h-screen w-full bg-[#F8FAFC] overflow-hidden text-[#1E293B] font-sans">
      {/* Sidebar */}
      <aside className="w-[240px] flex-shrink-0 bg-white border-r border-slate-200 flex flex-col justify-between shadow-sm z-10">
        <div>
          <div className="p-6">
            <h1 className="text-2xl font-bold text-[#4F46E5] tracking-tight">CapacitaYa</h1>
          </div>
          <nav className="px-4 space-y-1">
            {links.map((link) => {
              const Icon = link.icon;
              const isActive = activePage === link.name;
              return (
                <Link key={link.name} href={link.path}>
                  <div
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors cursor-pointer ${
                      isActive
                        ? "bg-indigo-50 text-[#4F46E5]"
                        : "text-[#64748B] hover:text-[#1E293B] hover:bg-slate-50"
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    {link.name}
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>

        {isCandidato && (
          <div className="p-4 mt-auto">
            <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
              <div className="text-xs font-semibold text-[#64748B] mb-3 uppercase tracking-wider">Tu Tutora</div>
              <div className="flex items-center gap-3 mb-3">
                <div className="relative">
                  <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-[#4F46E5] font-bold">
                    AG
                  </div>
                  <div className="absolute bottom-0 right-0 w-3 h-3 bg-[#10B981] border-2 border-white rounded-full"></div>
                </div>
                <div>
                  <div className="font-semibold text-sm">Ana García</div>
                  <div className="text-xs text-[#10B981]">En línea</div>
                </div>
              </div>
              <Link href="/canal-tutor">
                <button className="w-full py-2 bg-white border border-slate-200 text-sm font-medium rounded-xl text-[#1E293B] hover:bg-slate-50 transition-colors">
                  Enviar mensaje
                </button>
              </Link>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Topbar */}
        <header className="h-[72px] flex-shrink-0 bg-white border-b border-slate-200 flex items-center justify-between px-8 z-10">
          <h2 className="text-xl font-bold text-[#1E293B]">{activePage}</h2>
          <div className="flex items-center gap-6">
            
            <Link href="/dashboard-tutor">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-indigo-50 border border-indigo-100 rounded-xl text-xs font-semibold text-[#4F46E5] hover:bg-indigo-100 transition-all cursor-pointer">
                <BarChart3 className="w-3.5 h-3.5" />
                Vista Tutor (CAME)
              </div>
            </Link>

            <button className="relative text-[#64748B] hover:text-[#1E293B] transition-colors">
              <Bell className="w-6 h-6" />
              <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white"></span>
            </button>
            
            <div className="flex items-center gap-3 border-l border-slate-200 pl-6">
              <div className="text-right hidden sm:block">
                <div className="text-sm font-semibold">{userName}</div>
                <div className="text-xs text-[#64748B] capitalize">{userRole}</div>
              </div>
              <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 font-bold">
                {initials}
              </div>
            </div>
          </div>
        </header>

        {/* Scrollable Area */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
