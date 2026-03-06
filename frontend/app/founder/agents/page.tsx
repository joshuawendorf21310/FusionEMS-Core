"use client";

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API } from "@/services/api";

type Subnet = {
  name: string;
  status: string;
  throughput: string;
  last_action: string;
};

type AgentState = {
  id: string;
  name: string;
  type: string;
  status: string;
  uptime: string;
  subnets: Subnet[];
  cpu_load?: string;
  mem_usage?: string;
};

type GlobalLog = {
  id: string;
  timestamp: string;
  text: string;
  agentName: string;
  isCommand?: boolean;
};

export default function AgentsIntelligenceMatrix() {
  const [agents, setAgents] = useState<AgentState[]>([]);
  const [connectionStatus, setConnectionStatus] = useState("CONNECTING...");
  const [logs, setLogs] = useState<GlobalLog[]>([]);
  const [commandInput, setCommandInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") || "";
    const es = new EventSource(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/founder/agents/stream?token=${encodeURIComponent(token)}`);

    es.onopen = () => setConnectionStatus("LINK ESTABLISHED");
    es.onerror = () => setConnectionStatus("SIGNAL LOST - RETRYING...");

    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const timeStr = new Date().toISOString().substring(11, 23);
        
        if (payload.type === "init") {
          setAgents(payload.agents);
        } else if (payload.type === "command_start" || payload.type === "command_end") {
           setLogs((lPrev) => [
              {
                id: `${Date.now()}-${Math.random()}`,
                timestamp: timeStr,
                text: payload.type === "command_start" ? `> EXECUTING COMMAND: ${payload.command}` : `> COMMAND COMPLETE: ${payload.command}`,
                agentName: "SYS_ROOT",
                isCommand: true,
              },
              ...lPrev,
            ].slice(0, 100));
        } else if (payload.type === "telemetry") {
          setAgents((prev) =>
            prev.map((agt) => {
              if (agt.id === payload.agent_id) {
                const newAgt = { ...agt, cpu_load: payload.cpu_load, mem_usage: payload.mem_usage };
                newAgt.subnets = [...agt.subnets];
                if (newAgt.subnets[payload.subagent_idx]) {
                  newAgt.subnets[payload.subagent_idx].status = payload.status;
                  newAgt.subnets[payload.subagent_idx].throughput = payload.throughput;
                  newAgt.subnets[payload.subagent_idx].last_action = payload.last_action;
                }
                
                // Add log
                setLogs((lPrev) => {
                  const newLogs = [
                    {
                      id: `${Date.now()}-${Math.random()}`,
                      timestamp: timeStr,
                      text: `[${newAgt.subnets[payload.subagent_idx].name}] ${payload.last_action}`,
                      agentName: newAgt.name,
                    },
                    ...lPrev,
                  ];
                  return newLogs.slice(0, 100); // keep last 100
                });
                
                return newAgt;
              }
              return agt;
            })
          );
        }
      } catch (err) {
        console.error("Parse error in stream:", err);
      }
    };

    return () => es.close();
  }, []);

  const handleCommandSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commandInput.trim()) return;
    setIsSending(true);
    try {
      const token = localStorage.getItem("token") || "";
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/founder/agents/command`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ command: commandInput }),
      });
      setCommandInput("");
    } catch(err) {
      console.error(err);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] text-[#00ffcc] p-6 font-mono overflow-hidden relative flex flex-col">
      {/* Heavy CRT / Scanline background */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-[0.03] z-50 mix-blend-overlay"
        style={{
          backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 2px, #00ffcc 2px, #00ffcc 4px)"
        }}
      />
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(0,0,0,0.8)_100%)] z-40" />

      <header className="flex-none mb-6 flex justify-between items-end border-b border-[#00ffcc]/30 pb-4 relative z-10">
        <div>
          <motion.h1 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-4xl font-extrabold uppercase tracking-widest text-[#00ffcc] drop-shadow-[0_0_8px_rgba(0,255,204,0.8)]"
          >
            Autonomous Swarm Matrix
          </motion.h1>
          <div className="text-sm mt-2 font-bold tracking-wider text-[#00ffcc]/60 uppercase flex items-center space-x-3">
            <span>UPLINK:</span>
            <span className={connectionStatus === "LINK ESTABLISHED" ? "text-green-400 drop-shadow-[0_0_5px_#4ade80]" : "text-red-500 animate-pulse"}>
              {connectionStatus}
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold font-mono tracking-widest text-white drop-shadow-[0_0_4px_#ffffff]">DOMINATION.OS</div>
          <div className="text-xs text-[#00ffcc]/50 uppercase mt-1">Global Intelligence Grid Active</div>
        </div>
      </header>

      <div className="flex-1 flex flex-col xl:flex-row gap-6 relative z-10 min-h-0">
        
        {/* Left pane: Agents Array */}
        <div className="flex-1 overflow-y-auto pr-4 space-y-6 scrollbar-hide">
          <AnimatePresence>
            {agents.map((agent, i) => (
              <motion.div
                key={agent.id}
                initial={{ opacity: 0, scale: 0.95, x: -50 }}
                animate={{ opacity: 1, scale: 1, x: 0 }}
                transition={{ delay: i * 0.1, duration: 0.4 }}
                className="relative group border border-[#00ffcc]/30 bg-black/60 backdrop-blur-md p-6"
                style={{
                  clipPath: "polygon(0 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%)",
                  boxShadow: "inset 0 0 20px rgba(0, 255, 204, 0.05)"
                }}
              >
                {/* Visual accents */}
                <div className="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-[#00ffcc]"></div>
                <div className="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-[#00ffcc]"></div>
                
                <div className="flex justify-between items-start mb-6 border-b border-[#00ffcc]/20 pb-4">
                  <div>
                    <h2 className="text-2xl font-bold uppercase tracking-wider drop-shadow-[0_0_5px_rgba(0,255,204,0.6)]">{agent.name}</h2>
                    <div className="text-xs text-[#00ffcc]/60 uppercase mt-1 tracking-widest">Class: {agent.type}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-light tabular-nums leading-none tracking-tighter text-white drop-shadow-[0_0_8px_#ffffff]">
                      {agent.cpu_load || "0%"}
                    </div>
                    <div className="text-[10px] text-[#00ffcc]/50 uppercase tracking-widest mt-1">CPU UTIL // {agent.mem_usage || "0GB"} RAM</div>
                  </div>
                </div>

                <div className="space-y-3">
                  {agent.subnets.map((sub, j) => (
                    <motion.div 
                      key={j}
                      layout
                      className="p-3 border-l-2 border-[#00ffcc]/30 bg-gradient-to-r from-[#00ffcc]/[0.08] to-transparent flex items-center justify-between"
                    >
                      <div className="flex flex-col w-1/3">
                        <span className="text-sm font-bold uppercase text-white truncate">{sub.name}</span>
                        <span className="text-[10px] text-[#00ffcc]/60 mt-1 uppercase tracking-widest">SUBNODE {j + 1}</span>
                      </div>

                      <div className="flex-1 px-4 flex items-center space-x-3">
                         <div className={`w-3 h-3 rounded-full flex-shrink-0 ${sub.status === 'idle' ? 'bg-[#00ffcc]/20' : 'bg-[#00ffcc] animate-pulse shadow-[0_0_10px_#00ffcc]'}`} />
                         <div className="flex flex-col">
                           <span className="text-[10px] uppercase font-bold text-[#00ffcc]/80 tracking-widest">{sub.status}</span>
                           <span className="text-xs opacity-70 truncate max-w-[200px] text-white/80">{sub.last_action}</span>
                         </div>
                      </div>

                      <div className="w-24 text-right flex flex-col justify-center">
                        <div className="text-lg font-bold tabular-nums text-white drop-shadow-[0_0_2px_#ffffff]">{sub.throughput}</div>
                        <div className="text-[9px] text-[#00ffcc]/50 uppercase tracking-widest">OPS/SEC</div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Right pane: Global Telemetry + Command Core */}
        <div className="w-full xl:w-[450px] flex flex-col gap-4">
            
            {/* Live Feed */}
            <div className="flex-1 flex flex-col border border-[#00ffcc]/30 bg-black/60 relative overflow-hidden min-h-[300px]" style={{
                clipPath: "polygon(20px 0, 100% 0, 100% 100%, 0 100%, 0 20px)",
            }}>
              <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-[#00ffcc]"></div>
              
              <div className="bg-[#00ffcc]/10 text-center py-2 border-b border-[#00ffcc]/30 text-xs font-bold tracking-[0.2em] uppercase">
                Live Execution Feed
              </div>
              
              <div className="flex-1 overflow-y-auto p-4 space-y-2 flex flex-col-reverse">
                <AnimatePresence>
                  {logs.map((log) => (
                    <motion.div
                      key={log.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ duration: 0.2 }}
                      className={`text-xs font-mono break-all py-1 border-b border-[#00ffcc]/10 ${log.isCommand ? 'bg-[#00ffcc]/20 font-bold border-l-2 border-[#00ffcc] pl-2' : ''}`}
                    >
                      <span className="text-[#00ffcc]/50 mr-2">[{log.timestamp}]</span>
                      <span className={log.isCommand ? "text-[#00ffcc] drop-shadow-[0_0_2px_#00ffcc]" : "text-white font-bold"}>{log.agentName}</span>
                      <span className={`${log.isCommand ? "text-white" : "text-[#00ffcc]"} ml-2`}>{log.text}</span>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>

            {/* Command Input Matrix */}
            <div className="flex-none border border-[#00ffcc]/30 bg-black/80 relative p-4" style={{
                 clipPath: "polygon(0 0, 100% 0, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0 100%)",
                 boxShadow: "0 0 15px rgba(0, 255, 204, 0.1)"
            }}>
               <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-[#00ffcc]"></div>
               <div className="text-[10px] text-[#00ffcc]/60 uppercase tracking-[0.2em] mb-2 flex items-center space-x-2">
                 <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse shadow-[0_0_8px_red]"></div>
                 <span>Direct Override Command</span>
               </div>
               
               <form onSubmit={handleCommandSubmit} className="flex">
                  <span className="text-[#00ffcc] font-bold text-lg mr-2 leading-none font-mono py-2">$&gt;</span>
                  <input
                    type="text"
                    value={commandInput}
                    onChange={(e) => setCommandInput(e.target.value)}
                    placeholder="Enter swarm directive..."
                    disabled={isSending}
                    className="flex-1 bg-transparent text-white font-mono placeholder:text-[#00ffcc]/30 focus:outline-none focus:border-none focus:ring-0 border-b border-[#00ffcc]/30 text-sm py-1"
                  />
                  <button 
                    type="submit" 
                    disabled={isSending || !commandInput.trim()}
                    className="ml-4 px-4 py-1 text-xs uppercase font-bold tracking-widest bg-[#00ffcc]/10 text-[#00ffcc] border border-[#00ffcc]/50 hover:bg-[#00ffcc] hover:text-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Exe
                  </button>
               </form>
            </div>
            
        </div>
      </div>
    </div>
  );
}
