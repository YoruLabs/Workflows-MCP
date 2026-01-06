"use client";

import { useState } from "react";
import { 
  Search, 
  Linkedin, 
  MapPin, 
  Briefcase, 
  Building2, 
  Loader2, 
  Filter,
  Users,
  CheckCircle2,
  Circle,
  Sparkles,
  MessageCircleQuestion,
  ArrowRight,
  SkipForward
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Lead {
  full_name?: string;
  title?: string;
  company_name?: string;
  linkedin_url?: string;
  location?: string;
}

interface ProgressStep {
  id: string;
  message: string;
  status: "pending" | "active" | "complete";
}

interface ClarifyQuestion {
  id: string;
  question: string;
  options?: string[];
}

interface ClarificationState {
  isOpen: boolean;
  questions: ClarifyQuestion[];
  answers: Record<string, string>;
  reason?: string;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(5);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [clarifying, setClarifying] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([]);
  const [clarification, setClarification] = useState<ClarificationState>({
    isOpen: false,
    questions: [],
    answers: {},
  });

  // Phase 1: Check if query needs clarification
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setClarifying(true);
    setError("");

    try {
      const res = await fetch("/api/clarify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      const data = await res.json();

      if (data.needs_clarification && data.questions?.length > 0) {
        // Show clarification panel
        setClarification({
          isOpen: true,
          questions: data.questions,
          answers: {},
          reason: data.reason,
        });
        setClarifying(false);
        return;
      }

      // No clarification needed, proceed to search
      setClarifying(false);
      runSearch(query);
    } catch (err: any) {
      setClarifying(false);
      // If clarify fails, just run the search
      runSearch(query);
    }
  };

  // Handle answer selection
  const setAnswer = (questionId: string, value: string) => {
    setClarification(prev => ({
      ...prev,
      answers: { ...prev.answers, [questionId]: value },
    }));
  };

  // Phase 2: Run search with enriched query
  const runSearch = async (enrichedQuery: string) => {
    setLoading(true);
    setHasSearched(true);
    setLeads([]);
    setClarification({ isOpen: false, questions: [], answers: {} });
    setProgressSteps([
      { id: "starting", message: "Starting pipeline...", status: "active" }
    ]);

    try {
      const response = await fetch("/api/pipeline/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: enrichedQuery, limit, useApify: true }),
      });

      if (!response.body) {
        throw new Error("No response body");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) continue;
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.step) {
                setProgressSteps(prev => {
                  const updated = prev.map(s => ({ ...s, status: "complete" as const }));
                  return [...updated, { id: data.step, message: data.message, status: "active" as const }];
                });
              }
              if (data.leads) setLeads(data.leads);
              if (data.error) setError(data.message || "Pipeline error");
            } catch {}
          }
        }
      }

      setProgressSteps(prev => prev.map(s => ({ ...s, status: "complete" as const })));

    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Build enriched query from answers
  const handleContinueWithAnswers = () => {
    const parts = [query];
    const { answers, questions } = clarification;
    
    // Add ALL answer values to the query
    // Match each answer to its question for context
    questions.forEach((q) => {
      const answer = answers[q.id];
      if (answer && answer !== "Other") {
        parts.push(answer);
      }
    });
    
    const enrichedQuery = parts.join(" ");
    console.log("🔍 Enriched Query:", enrichedQuery);
    console.log("📝 Answers:", answers);
    
    runSearch(enrichedQuery);
  };

  // Skip clarification and search with original query
  const handleSkipClarification = () => {
    runSearch(query);
  };

  return (
    <div className="min-h-screen w-full relative overflow-hidden bg-zinc-950 font-sans selection:bg-indigo-500/20">
      
      {/* Background Ambience */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[400px] bg-indigo-500/20 blur-[120px] rounded-full pointer-events-none opacity-50" />
      
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
        
        {/* Header Section */}
        <div className="max-w-3xl mx-auto text-center space-y-6 mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium uppercase tracking-wide">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
            </span>
            AI Pipeline Active
          </div>
          
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white">
            Find your next <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">ideal customer</span>
          </h1>
          
          <p className="text-lg text-zinc-400 max-w-xl mx-auto leading-relaxed">
            Enter a natural language query to discover and enrich B2B leads automatically. Powered by Apify, Clay, and OpenAI.
          </p>
        </div>

        {/* Search Interface */}
        <div className="max-w-3xl mx-auto mb-20 relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
          
          <form 
            onSubmit={handleSearch} 
            className="relative flex items-center gap-1 sm:gap-2 bg-zinc-900 border border-zinc-800 p-2 rounded-xl shadow-2xl focus-within:ring-2 focus-within:ring-indigo-500/50 focus-within:border-indigo-500/50 transition-all"
          >
            <div className="pl-3 sm:pl-4 text-zinc-500 shrink-0">
              <Search className="w-5 h-5" />
            </div>
            
            <input
              type="text"
              placeholder="e.g. Marketing Directors..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 bg-transparent border-none text-white placeholder:text-zinc-600 focus:outline-none focus:ring-0 px-2 py-3 text-base md:text-lg min-w-0"
            />
            
            <div className="h-6 w-px bg-zinc-800 mx-1 hidden sm:block"></div>
            
            {/* Unified Custom Dropdown */}
            <div className="relative z-50 shrink-0">
              <button
                type="button"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center gap-2 text-zinc-400 text-sm font-medium hover:text-white transition-colors px-2 sm:px-3 py-2 rounded-lg hover:bg-zinc-800 focus:outline-none"
              >
                {/* Mobile: Filter Icon Only / Desktop: Text + Icon */}
                <span className="hidden sm:inline">{limit} results</span>
                <span className="sm:hidden">{limit}</span>
                <Filter className="w-3 h-3" />
              </button>

              {isDropdownOpen && (
                <>
                  <div 
                    className="fixed inset-0 z-40" 
                    onClick={() => setIsDropdownOpen(false)}
                  ></div>
                  <div className="absolute right-0 top-full mt-2 w-48 bg-zinc-900 border border-zinc-800 rounded-xl shadow-xl overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-200">
                    {[5, 10, 20, 50].map((val) => (
                      <button
                        key={val}
                        type="button"
                        onClick={() => {
                          setLimit(val);
                          setIsDropdownOpen(false);
                        }}
                        className={cn(
                          "w-full text-left px-4 py-3 text-sm transition-colors hover:bg-zinc-800",
                          limit === val ? "text-indigo-400 bg-indigo-400/10" : "text-zinc-400"
                        )}
                      >
                        {val} results
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || clarifying}
              className="bg-white text-zinc-950 hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed font-semibold py-3 px-4 sm:px-6 rounded-lg transition-all flex items-center gap-2 shadow-lg shadow-white/5 shrink-0"
            >
              {clarifying ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span className="hidden sm:inline">Search</span>
                  <span className="sm:hidden"><Search className="w-4 h-4"/></span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Clarification Panel */}
        {clarification.isOpen && (
          <div className="max-w-2xl mx-auto mb-10 animate-in slide-in-from-top-4 duration-300">
            <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 rounded-2xl p-6 shadow-xl">
              <div className="flex items-start gap-4 mb-6">
                <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center shrink-0">
                  <MessageCircleQuestion className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-white font-semibold mb-1">Let me help refine your search</h3>
                  <p className="text-zinc-400 text-sm">{clarification.reason || "A few quick questions to find better matches:"}</p>
                </div>
              </div>

              <div className="space-y-4 mb-6">
                {clarification.questions.map((q, idx) => (
                  <div key={idx} className="space-y-2">
                    <label className="text-sm text-zinc-300 font-medium">{q.question}</label>
                    <div className="flex flex-wrap gap-2">
                      {q.options?.map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => setAnswer(q.id, opt)}
                          className={cn(
                            "px-3 py-1.5 text-sm rounded-lg border transition-all",
                            clarification.answers[q.id] === opt
                              ? "bg-indigo-500 border-indigo-400 text-white"
                              : "bg-zinc-800/50 border-zinc-700 text-zinc-300 hover:border-zinc-500"
                          )}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={handleSkipClarification}
                  className="text-zinc-400 hover:text-white text-sm font-medium flex items-center gap-1 transition-colors"
                >
                  <SkipForward className="w-4 h-4" />
                  Skip
                </button>
                <button
                  type="button"
                  onClick={handleContinueWithAnswers}
                  className="bg-indigo-500 hover:bg-indigo-400 text-white font-semibold py-2 px-4 rounded-lg flex items-center gap-2 transition-colors"
                >
                  Continue
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
           <div className="max-w-2xl mx-auto mb-10 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm text-center">
             {error}
           </div>
        )}

        {/* LOADING STATE - Progress Steps */}
        {loading && (
          <div className="max-w-xl mx-auto">
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 shadow-xl">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-indigo-400 animate-pulse" />
                </div>
                <div>
                  <h3 className="text-white font-semibold">AI Pipeline Running</h3>
                  <p className="text-zinc-500 text-sm">Processing your request...</p>
                </div>
              </div>
              
              <div className="space-y-3">
                {progressSteps.map((step, idx) => (
                  <div 
                    key={idx} 
                    className={cn(
                      "flex items-center gap-3 p-3 rounded-lg transition-all duration-300",
                      step.status === "active" && "bg-indigo-500/10 border border-indigo-500/20",
                      step.status === "complete" && "opacity-70"
                    )}
                  >
                    {step.status === "complete" ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0" />
                    ) : step.status === "active" ? (
                      <Loader2 className="w-5 h-5 text-indigo-400 animate-spin shrink-0" />
                    ) : (
                      <Circle className="w-5 h-5 text-zinc-600 shrink-0" />
                    )}
                    <span className={cn(
                      "text-sm",
                      step.status === "active" && "text-white",
                      step.status === "complete" && "text-zinc-400",
                      step.status === "pending" && "text-zinc-600"
                    )}>
                      {step.message}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* RESULTS */}
        {!loading && hasSearched && leads.length === 0 && !error && (
            <div className="text-center py-20 text-zinc-500">
                <Users className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p>No leads found matching your criteria.</p>
            </div>
        )}

        {!loading && leads.length > 0 && (
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-6 px-2">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                    Results <span className="text-zinc-500 text-sm font-normal">({leads.length} found)</span>
                </h2>
                <button className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors">
                    Export CSV
                </button>
            </div>

            {/* Desktop View */}
            <div className="hidden md:block overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/30 backdrop-blur-sm shadow-2xl">
              <table className="w-full text-left">
                <thead className="bg-zinc-900 text-zinc-400 uppercase tracking-wider text-xs border-b border-zinc-800">
                  <tr>
                    <th className="px-6 py-4 font-medium">Professional</th>
                    <th className="px-6 py-4 font-medium">Role</th>
                    <th className="px-6 py-4 font-medium">Company</th>
                    <th className="px-6 py-4 font-medium">Location</th>
                    <th className="px-6 py-4 text-right font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/50">
                  {leads.map((lead, idx) => (
                    <tr key={idx} className="group hover:bg-zinc-800/30 transition-colors duration-200">
                      
                      {/* Name */}
                      <td className="px-6 py-4">
                        <div className="font-medium text-white group-hover:text-indigo-300 transition-colors">
                          {lead.full_name || "Unknown"}
                        </div>
                      </td>

                      {/* Role */}
                      <td className="px-6 py-4 text-zinc-300 text-sm">
                        <div className="flex items-center gap-2">
                            <Briefcase className="w-3 h-3 text-zinc-500" />
                            <span className="truncate max-w-[200px]" title={lead.title}>{lead.title || "—"}</span>
                        </div>
                      </td>

                      {/* Company */}
                      <td className="px-6 py-4 text-zinc-300 text-sm">
                        <div className="flex items-center gap-2">
                            <Building2 className="w-3 h-3 text-zinc-500" />
                            <span className="truncate max-w-[200px]" title={lead.company_name}>{lead.company_name || "—"}</span>
                        </div>
                      </td>

                      {/* Location */}
                      <td className="px-6 py-4 text-zinc-400 text-sm">
                        <div className="flex items-center gap-2">
                            <MapPin className="w-3 h-3 text-zinc-600" />
                            {lead.location || "—"}
                        </div>
                      </td>

                      {/* Action */}
                      <td className="px-6 py-4 text-right">
                        {lead.linkedin_url ? (
                          <a 
                            href={lead.linkedin_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-zinc-800 hover:bg-blue-600 text-zinc-400 hover:text-white transition-all group-hover:scale-110"
                            title="View on LinkedIn"
                          >
                            <Linkedin className="w-4 h-4" />
                          </a>
                        ) : (
                          <span className="text-zinc-600">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Card View */}
            <div className="md:hidden space-y-4">
              {leads.map((lead, idx) => (
                <div key={idx} className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5 shadow-sm space-y-4 hover:border-zinc-700 transition-colors active:scale-[0.99]">
                    <div className="flex justify-between items-start">
                        <div>
                            <h3 className="text-white font-semibold text-lg">{lead.full_name}</h3>
                            <p className="text-indigo-400 text-sm font-medium mt-0.5">{lead.title}</p>
                        </div>
                        {lead.linkedin_url && (
                            <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer" className="p-2 bg-blue-600/10 text-blue-500 rounded-full hover:bg-blue-600 hover:text-white transition-colors">
                                <Linkedin className="w-5 h-5" />
                            </a>
                        )}
                    </div>
                    
                    <div className="space-y-2 pt-2 border-t border-zinc-800/50">
                        <div className="flex items-center gap-3 text-sm text-zinc-400">
                            <Building2 className="w-4 h-4 text-zinc-600" />
                            {lead.company_name}
                        </div>
                        <div className="flex items-center gap-3 text-sm text-zinc-400">
                            <MapPin className="w-4 h-4 text-zinc-600" />
                            {lead.location}
                        </div>
                    </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
