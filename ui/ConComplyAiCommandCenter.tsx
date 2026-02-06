import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  DollarSign, 
  FileText, 
  Map as MapIcon, 
  Zap,
  Shield,
  Search,
  Target,
  TrendingUp,
  Eye,
  EyeOff,
  Hash,
  Scale,
  Filter,
  X,
  ChevronRight
} from 'lucide-react';

// ==================== TYPES ====================
interface Project {
  bbl: string;
  bin: string;
  address: string;
  borough: string;
  lat: number;
  lng: number;
  contestableWork: number;
  violations: string[];
  status: 'flagged' | 'processing' | 'resolved';
  superintendentConflict?: boolean;
  superintendentId?: string; // For One-Job tracking
  superintendentJobCount?: number; // Cross-referenced from DOB NOW
  ll152District?: number;
  buildingType?: 'residential' | 'commercial' | 'mixed-use'; // LL152 Feb 22 scope
  filingDate: Date;
  lastActivity: Date;
  auditHash?: string;
  hpdRegistrationNumber?: string; // CRITICAL: LL86 compliance (#1 audit failure)
}

interface HandshakeEvent {
  id: string;
  timestamp: Date;
  bbl: string;
  address: string;
  agent: 'Scout' | 'Guard' | 'Fixer';
  action: string;
  severity: 'low' | 'medium' | 'high';
}

interface AuditReceipt {
  bbl: string;
  address: string;
  hash: string;
  legalBasis: string;
  suggestedAction: string;
  estimatedSavings: number;
  complianceRisk: string;
  timestamp: Date;
  humanTime: string;
  humanCost: number;
  agentTime: string;
  agentCost: number;
}

// ==================== MOCK DATA GENERATORS ====================
const VIOLATIONS = [
  'LL149 Multi-Site Superintendent',
  'LL152 Compliance Cycle Violation',
  'RCNY 101-08 Documentation Gap',
  'DOB NOW Filing Inconsistency',
  'Missing C of O Documentation',
  'Superintendent License Expired'
];

const ADDRESSES = [
  { addr: '432 Park Avenue', borough: 'Manhattan', lat: 40.7614, lng: -73.9718 },
  { addr: '56 Leonard Street', borough: 'Manhattan', lat: 40.7178, lng: -74.0059 },
  { addr: '111 West 57th Street', borough: 'Manhattan', lat: 40.7649, lng: -73.9794 },
  { addr: '220 Central Park South', borough: 'Manhattan', lat: 40.7664, lng: -73.9799 },
  { addr: '15 Hudson Yards', borough: 'Manhattan', lat: 40.7536, lng: -74.0010 },
  { addr: '30 Park Place', borough: 'Manhattan', lat: 40.7130, lng: -74.0088 },
  { addr: '252 East 57th Street', borough: 'Manhattan', lat: 40.7587, lng: -73.9654 },
  { addr: '520 Park Avenue', borough: 'Manhattan', lat: 40.7642, lng: -73.9686 },
  { addr: '9 DeKalb Avenue', borough: 'Brooklyn', lat: 40.6917, lng: -73.9808 },
  { addr: '300 Ashland Place', borough: 'Brooklyn', lat: 40.6865, lng: -73.9784 },
  { addr: '10 Nevins Street', borough: 'Brooklyn', lat: 40.6882, lng: -73.9806 },
  { addr: '388 Bridge Street', borough: 'Brooklyn', lat: 40.6953, lng: -73.9837 },
  { addr: '23-15 44th Drive', borough: 'Queens', lat: 40.7481, lng: -73.9483 },
  { addr: '27-01 Queens Plaza North', borough: 'Queens', lat: 40.7503, lng: -73.9386 },
];

const generateBBL = (index: number): string => {
  const borough = (index % 5) + 1;
  const block = 1000 + (index * 42);
  const lot = 1 + (index % 9999);
  return `${borough}-${String(block).padStart(5, '0')}-${String(lot).padStart(4, '0')}`;
};

const generateBIN = (index: number): string => {
  return `${1000000 + index * 137}`;
};

const generateMockProjects = (): Project[] => {
  const buildingTypes: Array<'residential' | 'commercial' | 'mixed-use'> = [
    'residential', 'commercial', 'mixed-use'
  ];
  
  return ADDRESSES.map((loc, idx) => {
    const buildingType = buildingTypes[idx % 3];
    const filingDate = new Date(2026, Math.floor(Math.random() * 12), Math.floor(Math.random() * 28) + 1);
    const superintendentId = `SUP-${1000 + idx}`;
    const superintendentJobCount = Math.random() > 0.6 ? Math.floor(Math.random() * 3) + 1 : 1;
    
    return {
      bbl: generateBBL(idx),
      bin: generateBIN(idx),
      address: loc.addr,
      borough: loc.borough,
      lat: loc.lat + (Math.random() - 0.5) * 0.002,
      lng: loc.lng + (Math.random() - 0.5) * 0.002,
      contestableWork: Math.floor(Math.random() * 50000000) + 1000000,
      violations: VIOLATIONS.slice(0, Math.floor(Math.random() * 3) + 1),
      status: ['flagged', 'processing', 'resolved'][Math.floor(Math.random() * 3)] as any,
      superintendentConflict: superintendentJobCount > 1,
      superintendentId,
      superintendentJobCount,
      ll152District: [4, 6, 8, 9, 16][Math.floor(Math.random() * 5)],
      buildingType,
      filingDate,
      lastActivity: new Date(Date.now() - Math.random() * 3600000),
      auditHash: `sha256:${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`,
      hpdRegistrationNumber: `HPD-${100000 + idx}` // CRITICAL for LL86
    };
  });
};

const generateHandshakeEvents = (projects: Project[]): HandshakeEvent[] => {
  const events: HandshakeEvent[] = [];
  
  projects.slice(0, 15).forEach((proj, idx) => {
    const baseTime = Date.now() - (idx * 3000);
    
    events.push({
      id: `evt-${idx}-0`,
      timestamp: new Date(baseTime),
      bbl: proj.bbl,
      address: proj.address,
      agent: 'Scout',
      action: `Identified $${(proj.contestableWork / 1000000).toFixed(1)}M contestable work`,
      severity: 'medium'
    });
    
    if (proj.violations.length > 0) {
      events.push({
        id: `evt-${idx}-1`,
        timestamp: new Date(baseTime + 1200),
        bbl: proj.bbl,
        address: proj.address,
        agent: 'Guard',
        action: `Flagged ${proj.violations[0]}`,
        severity: proj.superintendentConflict ? 'high' : 'medium'
      });
    }
    
    events.push({
      id: `evt-${idx}-2`,
      timestamp: new Date(baseTime + 2400),
      bbl: proj.bbl,
      address: proj.address,
      agent: 'Fixer',
      action: 'Drafted broker outreach + audit receipt',
      severity: 'low'
    });
  });
  
  return events.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
};

// ==================== MAIN DASHBOARD COMPONENT ====================
export default function ConComplyAiCommandCenter() {
  const [projects] = useState<Project[]>(generateMockProjects());
  const [handshakeEvents, setHandshakeEvents] = useState<HandshakeEvent[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [shadowAuditMode, setShadowAuditMode] = useState(false);
  const [filterLL149, setFilterLL149] = useState(false);
  const [filterLL152, setFilterLL152] = useState(false);
  const [totalSavings, setTotalSavings] = useState(0);
  const [checksPerHour] = useState(14200);
  const eventContainerRef = useRef<HTMLDivElement>(null);

  // Initialize handshake events
  useEffect(() => {
    setHandshakeEvents(generateHandshakeEvents(projects));
  }, [projects]);

  // Animated savings counter
  useEffect(() => {
    const interval = setInterval(() => {
      setTotalSavings(prev => prev + Math.random() * 1247);
    }, 100);
    return () => clearInterval(interval);
  }, []);

  // Add new events periodically
  useEffect(() => {
    const interval = setInterval(() => {
      const randomProject = projects[Math.floor(Math.random() * projects.length)];
      const agents: Array<'Scout' | 'Guard' | 'Fixer'> = ['Scout', 'Guard', 'Fixer'];
      const randomAgent = agents[Math.floor(Math.random() * agents.length)];
      
      const actions = {
        Scout: [`Scanning BBL-${randomProject.bbl.split('-')[1]}`, `Found $${(Math.random() * 10).toFixed(1)}M exposure`],
        Guard: ['Validating compliance chain', 'Cross-referencing DOB records'],
        Fixer: ['Generating audit trail', 'Preparing lender package']
      };
      
      const newEvent: HandshakeEvent = {
        id: `evt-${Date.now()}`,
        timestamp: new Date(),
        bbl: randomProject.bbl,
        address: randomProject.address,
        agent: randomAgent,
        action: actions[randomAgent][Math.floor(Math.random() * actions[randomAgent].length)],
        severity: ['low', 'medium', 'high'][Math.floor(Math.random() * 3)] as any
      };
      
      setHandshakeEvents(prev => [newEvent, ...prev].slice(0, 50));
    }, 4000);
    
    return () => clearInterval(interval);
  }, [projects]);

  const filteredProjects = projects.filter(p => {
    if (filterLL149 && !p.superintendentConflict) return false;
    if (filterLL152 && ![4, 6, 8, 9, 16].includes(p.ll152District || 0)) return false;
    return true;
  });

  const generateAuditReceipt = (project: Project): AuditReceipt => {
    const humanTime = `${Math.floor(Math.random() * 20 + 5)} days`;
    const humanCost = Math.floor(Math.random() * 15000 + 5000);
    const agentTime = `${(Math.random() * 5 + 2).toFixed(1)} seconds`;
    const agentCost = parseFloat((Math.random() * 0.05 + 0.01).toFixed(4));
    
    return {
      bbl: project.bbl,
      address: project.address,
      hash: project.auditHash || `sha256:${Math.random().toString(36).substr(2, 16)}`,
      legalBasis: project.violations[0] === 'LL149 Multi-Site Superintendent' 
        ? 'RCNY §101-08: Superintendent must be dedicated to single construction site'
        : 'NYC Building Code §28-211.1: All construction work requires compliant oversight',
      suggestedAction: 'Engage licensed broker to source compliant superintendent; notify lender of interim risk mitigation.',
      estimatedSavings: project.contestableWork * 0.15,
      complianceRisk: project.superintendentConflict ? 'HIGH - Multi-site violation' : 'MEDIUM - Documentation gap',
      timestamp: new Date(),
      humanTime,
      humanCost,
      agentTime,
      agentCost
    };
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-['JetBrains_Mono',monospace] overflow-hidden">
      {/* Ambient background effects */}
      <div className="fixed inset-0 opacity-20">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-amber-500/20 rounded-full blur-3xl animate-pulse" 
             style={{ animationDuration: '8s' }} />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse" 
             style={{ animationDuration: '12s', animationDelay: '2s' }} />
      </div>

      {/* Main container */}
      <div className="relative z-10">
        {/* HEADER - Economic Alpha */}
        <motion.header 
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="border-b border-amber-500/20 bg-slate-900/80 backdrop-blur-xl"
        >
          <div className="px-8 py-6">
            <div className="flex items-start justify-between mb-6">
              <div>
                <motion.h1 
                  className="text-4xl font-bold mb-2 bg-gradient-to-r from-amber-400 via-orange-400 to-emerald-400 bg-clip-text text-transparent"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3, duration: 0.6 }}
                >
                  ConComplyAi COMMAND CENTER
                </motion.h1>
                <motion.p 
                  className="text-slate-400 text-sm tracking-wider"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5, duration: 0.6 }}
                >
                  AUTONOMOUS CONSTRUCTION COMPLIANCE • TRIPLE HANDSHAKE PROTOCOL
                </motion.p>
              </div>
              
              <motion.button
                onClick={() => setShadowAuditMode(!shadowAuditMode)}
                className={`flex items-center gap-2 px-4 py-2 rounded border transition-all ${
                  shadowAuditMode 
                    ? 'bg-amber-500/20 border-amber-500 text-amber-400' 
                    : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-500'
                }`}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
              >
                {shadowAuditMode ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                <span className="text-xs font-semibold">SHADOW AUDIT</span>
              </motion.button>
            </div>

            {/* Economic Alpha Metrics */}
            <motion.div 
              className="grid grid-cols-4 gap-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.6 }}
            >
              {/* Real-time Savings Counter */}
              <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-emerald-500/30 rounded-lg p-4 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/0 via-emerald-500/10 to-emerald-500/0 animate-pulse" 
                     style={{ animationDuration: '3s' }} />
                <div className="relative">
                  <div className="flex items-center gap-2 mb-1">
                    <DollarSign className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs text-slate-400 uppercase tracking-wider">Real-Time Savings</span>
                  </div>
                  <div className="text-2xl font-bold text-emerald-400 font-mono">
                    ${totalSavings.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Human: $25/doc • Agent: $0.0007/doc
                  </div>
                </div>
              </div>

              {/* Throughput Metric */}
              <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-amber-500/30 rounded-lg p-4 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-amber-500/0 via-amber-500/10 to-amber-500/0 animate-pulse" 
                     style={{ animationDuration: '2s' }} />
                <div className="relative">
                  <div className="flex items-center gap-2 mb-1">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span className="text-xs text-slate-400 uppercase tracking-wider">Throughput</span>
                  </div>
                  <div className="text-2xl font-bold text-amber-400 font-mono">
                    {checksPerHour.toLocaleString()}/hr
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Compliance checks processed
                  </div>
                </div>
              </div>

              {/* Audit Trail Status */}
              <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-blue-500/30 rounded-lg p-4 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-blue-500/10 to-blue-500/0 animate-pulse" 
                     style={{ animationDuration: '4s' }} />
                <div className="relative">
                  <div className="flex items-center gap-2 mb-1">
                    <Hash className="w-4 h-4 text-blue-400" />
                    <span className="text-xs text-slate-400 uppercase tracking-wider">Audit Trail</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                    <div className="text-lg font-bold text-blue-400">ACTIVE</div>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Lender-ready SHA-256 hashing
                  </div>
                </div>
              </div>

              {/* Active Projects */}
              <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Activity className="w-4 h-4 text-slate-400" />
                  <span className="text-xs text-slate-400 uppercase tracking-wider">Active Projects</span>
                </div>
                <div className="text-2xl font-bold text-slate-200 font-mono">
                  {filteredProjects.length}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  ${(filteredProjects.reduce((sum, p) => sum + p.contestableWork, 0) / 1000000).toFixed(1)}M exposed
                </div>
              </div>
            </motion.div>
          </div>
        </motion.header>

        {/* MAIN CONTENT GRID */}
        <div className="grid grid-cols-12 gap-6 p-8 h-[calc(100vh-280px)]">
          {/* LEFT COLUMN - Interactive Map */}
          <motion.div 
            className="col-span-8"
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.8, duration: 0.6 }}
          >
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl h-full flex flex-col backdrop-blur-sm">
              {/* Map Header */}
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <MapIcon className="w-5 h-5 text-amber-400" />
                  <h2 className="text-lg font-bold text-slate-200">NYC SCOUT MAP</h2>
                  <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">
                    {filteredProjects.length} ACTIVE SITES
                  </span>
                </div>
                
                {/* Filter Controls */}
                <div className="flex gap-2">
                  <motion.button
                    onClick={() => setFilterLL149(!filterLL149)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-semibold border transition-all ${
                      filterLL149 
                        ? 'bg-red-500/20 border-red-500 text-red-400' 
                        : 'bg-slate-800/50 border-slate-700 text-slate-400'
                    }`}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Filter className="w-3 h-3" />
                    LL149 CONFLICTS
                  </motion.button>
                  
                  <motion.button
                    onClick={() => setFilterLL152(!filterLL152)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-semibold border transition-all ${
                      filterLL152 
                        ? 'bg-orange-500/20 border-orange-500 text-orange-400' 
                        : 'bg-slate-800/50 border-slate-700 text-slate-400'
                    }`}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Filter className="w-3 h-3" />
                    LL152 CYCLE
                  </motion.button>
                </div>
              </div>

              {/* Map Container (Simulated) */}
              <div className="flex-1 relative bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-hidden">
                {/* Grid overlay */}
                <div className="absolute inset-0 opacity-10"
                     style={{
                       backgroundImage: 'linear-gradient(rgba(148, 163, 184, 0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(148, 163, 184, 0.3) 1px, transparent 1px)',
                       backgroundSize: '40px 40px'
                     }}
                />

                {/* Project Markers */}
                <div className="absolute inset-0 p-8">
                  {filteredProjects.map((project, idx) => {
                    const x = ((project.lng + 74.1) / 0.3) * 100;
                    const y = ((40.9 - project.lat) / 0.15) * 100;
                    
                    return (
                      <motion.div
                        key={project.bbl}
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: 1 + (idx * 0.05), duration: 0.3 }}
                        style={{
                          position: 'absolute',
                          left: `${x}%`,
                          top: `${y}%`,
                        }}
                        className="relative group cursor-pointer"
                        onClick={() => setSelectedProject(project)}
                      >
                        {/* Pulsing ring */}
                        <div className={`absolute inset-0 -m-2 rounded-full animate-ping ${
                          project.superintendentConflict ? 'bg-red-500/50' : 'bg-amber-500/50'
                        }`} style={{ animationDuration: '3s' }} />
                        
                        {/* Marker dot */}
                        <motion.div 
                          className={`w-3 h-3 rounded-full border-2 relative z-10 ${
                            project.status === 'flagged' ? 'bg-red-500 border-red-300' :
                            project.status === 'processing' ? 'bg-amber-500 border-amber-300' :
                            'bg-emerald-500 border-emerald-300'
                          }`}
                          whileHover={{ scale: 1.5 }}
                        />
                        
                        {/* Hover tooltip */}
                        <motion.div 
                          initial={{ opacity: 0, y: 10 }}
                          whileHover={{ opacity: 1, y: 0 }}
                          className="absolute left-6 top-0 bg-slate-800 border border-slate-600 rounded-lg p-3 w-64 pointer-events-none z-50 shadow-2xl"
                        >
                          <div className="text-xs font-bold text-amber-400 mb-1">{project.address}</div>
                          <div className="text-xs text-slate-400 mb-2">BBL: {project.bbl}</div>
                          <div className="text-xs text-emerald-400 font-bold mb-1">
                            ${(project.contestableWork / 1000000).toFixed(1)}M Contestable Work
                          </div>
                          {project.violations.length > 0 && (
                            <div className="text-xs text-red-400 mt-2">
                              ⚠ {project.violations[0]}
                            </div>
                          )}
                        </motion.div>
                      </motion.div>
                    );
                  })}
                </div>

                {/* Borough labels */}
                <div className="absolute top-8 left-8 text-xs text-slate-600 font-bold space-y-1">
                  <div>MANHATTAN</div>
                  <div className="text-[10px] text-slate-700">40.7128° N, 74.0060° W</div>
                </div>

                {/* Legend */}
                <div className="absolute bottom-8 right-8 bg-slate-900/90 border border-slate-700 rounded-lg p-4 backdrop-blur">
                  <div className="text-xs font-bold text-slate-400 mb-3">STATUS LEGEND</div>
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-red-500 rounded-full" />
                      <span className="text-slate-400">Flagged (High Risk)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-amber-500 rounded-full" />
                      <span className="text-slate-400">Processing</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full" />
                      <span className="text-slate-400">Resolved</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* RIGHT COLUMN - Live Handshake Feed */}
          <motion.div 
            className="col-span-4"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.9, duration: 0.6 }}
          >
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl h-full flex flex-col backdrop-blur-sm">
              {/* Feed Header */}
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Activity className="w-5 h-5 text-emerald-400 animate-pulse" />
                  <h2 className="text-lg font-bold text-slate-200">LIVE HANDSHAKE</h2>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                  <span className="text-xs text-slate-500">LIVE</span>
                </div>
              </div>

              {/* Event Stream */}
              <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-900/50" ref={eventContainerRef}>
                <AnimatePresence mode="popLayout">
                  {handshakeEvents.map((event, idx) => {
                    const agentColors = {
                      Scout: 'from-blue-500/20 to-blue-600/10 border-blue-500/30',
                      Guard: 'from-amber-500/20 to-amber-600/10 border-amber-500/30',
                      Fixer: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30'
                    };

                    const agentIcons = {
                      Scout: Search,
                      Guard: Shield,
                      Fixer: Target
                    };

                    const AgentIcon = agentIcons[event.agent];

                    return (
                      <motion.div
                        key={event.id}
                        initial={{ opacity: 0, y: -20, x: 20 }}
                        animate={{ opacity: 1, y: 0, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.3 }}
                        className={`mx-3 my-2 p-3 rounded-lg border bg-gradient-to-br ${agentColors[event.agent]} hover:border-slate-600 transition-all cursor-pointer group`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <AgentIcon className="w-4 h-4" />
                            <span className="text-xs font-bold text-slate-200">{event.agent}</span>
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {event.timestamp.toLocaleTimeString('en-US', { hour12: false })}
                          </span>
                        </div>
                        
                        <div className="text-xs text-slate-300 mb-2 leading-relaxed">
                          {event.action}
                        </div>
                        
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-slate-500 font-mono">BBL-{event.bbl.split('-')[1]}</span>
                          <span className={`px-2 py-0.5 rounded ${
                            event.severity === 'high' ? 'bg-red-500/20 text-red-400' :
                            event.severity === 'medium' ? 'bg-amber-500/20 text-amber-400' :
                            'bg-emerald-500/20 text-emerald-400'
                          }`}>
                            {event.severity.toUpperCase()}
                          </span>
                        </div>

                        {/* Address on hover */}
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] text-slate-600 mt-1">
                          {event.address}
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>

              {/* Agent Status Bar */}
              <div className="p-4 border-t border-slate-800 grid grid-cols-3 gap-2">
                <div className="text-center">
                  <div className="text-xs text-blue-400 font-bold mb-1">SCOUT</div>
                  <div className="text-xs text-slate-500">Scanning</div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-amber-400 font-bold mb-1">GUARD</div>
                  <div className="text-xs text-slate-500">Validating</div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-emerald-400 font-bold mb-1">FIXER</div>
                  <div className="text-xs text-slate-500">Resolving</div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* DECISION PROOF MODAL */}
      <AnimatePresence>
        {selectedProject && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-8"
            onClick={() => setSelectedProject(null)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 50 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 50 }}
              transition={{ type: "spring", damping: 25 }}
              className="bg-slate-900 border-2 border-amber-500/50 rounded-2xl max-w-3xl w-full shadow-2xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="bg-gradient-to-r from-amber-500/10 to-emerald-500/10 border-b border-slate-800 p-6 flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <FileText className="w-6 h-6 text-amber-400" />
                    <h2 className="text-2xl font-bold text-slate-100">LENDER-READY AUDIT RECEIPT</h2>
                  </div>
                  <p className="text-sm text-slate-400">Cryptographically Signed Decision Proof</p>
                </div>
                <button
                  onClick={() => setSelectedProject(null)}
                  className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              {/* Modal Content */}
              <div className="p-6 space-y-6">
                {(() => {
                  const receipt = generateAuditReceipt(selectedProject);
                  
                  return (
                    <>
                      {/* Project Info */}
                      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-5">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-xs text-slate-500 mb-1">PROPERTY ADDRESS</div>
                            <div className="text-sm font-bold text-slate-200">{receipt.address}</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">BOROUGH</div>
                            <div className="text-sm font-bold text-slate-200">{selectedProject.borough}</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">BBL (BLOCK-BLOCK-LOT)</div>
                            <div className="text-sm font-mono font-bold text-amber-400">{receipt.bbl}</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">BIN (BUILDING ID)</div>
                            <div className="text-sm font-mono font-bold text-amber-400">{selectedProject.bin}</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">HPD REGISTRATION</div>
                            <div className="text-sm font-mono font-bold text-emerald-400">
                              {selectedProject.hpdRegistrationNumber || 'MISSING ⚠️'}
                            </div>
                            {!selectedProject.hpdRegistrationNumber && (
                              <div className="text-xs text-red-400 mt-1">⚠️ #1 LL86 audit failure cause</div>
                            )}
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">BUILDING TYPE</div>
                            <div className="text-sm font-bold text-slate-200 capitalize">
                              {selectedProject.buildingType || 'Unknown'}
                            </div>
                            {selectedProject.buildingType === 'commercial' && 
                             selectedProject.filingDate >= new Date('2026-02-22') && (
                              <div className="text-xs text-amber-400 mt-1">
                                ✓ Feb 22 scope: Now LL152
                              </div>
                            )}
                          </div>
                        </div>
                        
                        {/* One-Job Tracker */}
                        {selectedProject.superintendentId && (
                          <div className="mt-4 pt-4 border-t border-slate-700">
                            <div className="text-xs text-slate-500 mb-2">SUPERINTENDENT TRACKING</div>
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="text-xs font-mono text-slate-400">ID: {selectedProject.superintendentId}</div>
                                <div className={`text-sm font-bold mt-1 ${
                                  selectedProject.superintendentJobCount! > 1 ? 'text-red-400' : 'text-emerald-400'
                                }`}>
                                  {selectedProject.superintendentJobCount === 1 
                                    ? '✓ One-Job Compliant' 
                                    : `⚠️ Active on ${selectedProject.superintendentJobCount} sites (Job Juggling)`
                                  }
                                </div>
                              </div>
                              {selectedProject.superintendentJobCount! > 1 && 
                               selectedProject.filingDate < new Date('2026-01-01') && (
                                <div className="text-xs text-amber-400 bg-amber-500/10 px-2 py-1 rounded">
                                  Transition period ending soon
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* SHA-256 Hash */}
                      <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-5">
                        <div className="flex items-center gap-3 mb-3">
                          <Hash className="w-5 h-5 text-blue-400" />
                          <div className="text-sm font-bold text-slate-200">CRYPTOGRAPHIC AUDIT TRAIL</div>
                        </div>
                        <div className="font-mono text-xs text-blue-400 bg-slate-900/50 p-3 rounded break-all">
                          {receipt.hash}
                        </div>
                        <div className="text-xs text-slate-500 mt-2">
                          Timestamp: {receipt.timestamp.toISOString()}
                        </div>
                      </div>

                      {/* Compliance Risk */}
                      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-5">
                        <div className="flex items-center gap-3 mb-3">
                          <AlertTriangle className="w-5 h-5 text-red-400" />
                          <div className="text-sm font-bold text-slate-200">COMPLIANCE RISK ASSESSMENT</div>
                        </div>
                        <div className="text-lg font-bold text-red-400 mb-2">{receipt.complianceRisk}</div>
                        <div className="text-sm text-slate-300 space-y-2">
                          {selectedProject.violations.map((v, idx) => (
                            <div key={idx} className="flex items-start gap-2">
                              <span className="text-red-400">•</span>
                              <span>{v}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Legal Basis */}
                      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-5">
                        <div className="flex items-center gap-3 mb-3">
                          <Scale className="w-5 h-5 text-amber-400" />
                          <div className="text-sm font-bold text-slate-200">LEGAL BASIS</div>
                        </div>
                        <div className="text-sm text-slate-300 leading-relaxed">
                          {receipt.legalBasis}
                        </div>
                      </div>

                      {/* Suggested Action */}
                      <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-5">
                        <div className="flex items-center gap-3 mb-3">
                          <Target className="w-5 h-5 text-emerald-400" />
                          <div className="text-sm font-bold text-slate-200">FIXER RECOMMENDED ACTION</div>
                        </div>
                        <div className="text-sm text-slate-300 leading-relaxed">
                          {receipt.suggestedAction}
                        </div>
                      </div>

                      {/* Financial Impact */}
                      <div className="bg-gradient-to-r from-emerald-500/10 to-green-500/10 border border-emerald-500/30 rounded-lg p-5">
                        <div className="flex items-center gap-3 mb-3">
                          <DollarSign className="w-5 h-5 text-emerald-400" />
                          <div className="text-sm font-bold text-slate-200">ESTIMATED SAVINGS</div>
                        </div>
                        <div className="text-3xl font-bold text-emerald-400 mb-2">
                          ${receipt.estimatedSavings.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                        </div>
                        <div className="text-xs text-slate-500">
                          Based on {(receipt.estimatedSavings / selectedProject.contestableWork * 100).toFixed(1)}% of ${(selectedProject.contestableWork / 1000000).toFixed(1)}M contestable work
                        </div>
                      </div>

                      {/* Shadow Audit Comparison */}
                      {shadowAuditMode && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="bg-slate-800/80 border border-amber-500/30 rounded-lg p-5 backdrop-blur"
                        >
                          <div className="flex items-center gap-3 mb-4">
                            <Eye className="w-5 h-5 text-amber-400" />
                            <div className="text-sm font-bold text-slate-200">SHADOW AUDIT ANALYSIS</div>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-6">
                            {/* Human Team */}
                            <div className="bg-red-500/10 border border-red-500/20 rounded p-4">
                              <div className="text-xs text-slate-500 mb-2">TRADITIONAL HUMAN TEAM</div>
                              <div className="space-y-3">
                                <div>
                                  <div className="text-xs text-slate-400 mb-1">Time Required</div>
                                  <div className="text-xl font-bold text-red-400">{receipt.humanTime}</div>
                                </div>
                                <div>
                                  <div className="text-xs text-slate-400 mb-1">Estimated Cost</div>
                                  <div className="text-xl font-bold text-red-400">
                                    ${receipt.humanCost.toLocaleString()}
                                  </div>
                                </div>
                                <div className="text-xs text-slate-500 pt-2 border-t border-slate-700">
                                  Manual document review, cross-referencing, legal consultation
                                </div>
                              </div>
                            </div>

                            {/* AI Agents */}
                            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded p-4">
                              <div className="text-xs text-slate-500 mb-2">CONCOMPLYAI AGENTS</div>
                              <div className="space-y-3">
                                <div>
                                  <div className="text-xs text-slate-400 mb-1">Time Required</div>
                                  <div className="text-xl font-bold text-emerald-400">{receipt.agentTime}</div>
                                </div>
                                <div>
                                  <div className="text-xs text-slate-400 mb-1">Estimated Cost</div>
                                  <div className="text-xl font-bold text-emerald-400">
                                    ${receipt.agentCost.toFixed(4)}
                                  </div>
                                </div>
                                <div className="text-xs text-slate-500 pt-2 border-t border-slate-700">
                                  Automated Scout → Guard → Fixer pipeline
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Efficiency Gain */}
                          <div className="mt-4 pt-4 border-t border-slate-700 text-center">
                            <div className="text-xs text-slate-500 mb-1">EFFICIENCY MULTIPLIER</div>
                            <div className="text-2xl font-bold text-amber-400">
                              {(receipt.humanCost / receipt.agentCost).toLocaleString()}x faster, {((receipt.humanCost - receipt.agentCost) / receipt.humanCost * 100).toFixed(1)}% cheaper
                            </div>
                          </div>
                        </motion.div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex gap-3">
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-slate-900 font-bold py-3 px-6 rounded-lg transition-colors flex items-center justify-center gap-2"
                        >
                          <CheckCircle2 className="w-5 h-5" />
                          APPROVE & EXECUTE
                        </motion.button>
                        
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className="bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold py-3 px-6 rounded-lg transition-colors"
                        >
                          EXPORT PDF
                        </motion.button>
                      </div>
                    </>
                  );
                })()}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Custom scrollbar styles */}
      <style jsx global>{`
        .scrollbar-thin::-webkit-scrollbar {
          width: 6px;
        }
        .scrollbar-thin::-webkit-scrollbar-track {
          background: rgba(15, 23, 42, 0.5);
        }
        .scrollbar-thin::-webkit-scrollbar-thumb {
          background: rgba(71, 85, 105, 0.8);
          border-radius: 3px;
        }
        .scrollbar-thin::-webkit-scrollbar-thumb:hover {
          background: rgba(100, 116, 139, 0.9);
        }
      `}</style>
    </div>
  );
}
