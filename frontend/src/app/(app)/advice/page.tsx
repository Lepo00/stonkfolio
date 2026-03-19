"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  Send,
  AlertTriangle,
  CheckCircle2,
  Info,
} from "lucide-react";
import { usePortfolio } from "@/lib/portfolio-context";
import { getFullAdvice, sendAdviceChat } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import type {
  FullAdviceResponse,
  TopAction,
  Recommendation,
  Scenario,
  ChatMessage,
} from "@/types/api";

const labelClasses = "text-xs uppercase tracking-wider text-muted-foreground";

function scoreColor(score: number) {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-amber-500";
  return "text-red-500";
}

function scoreBgColor(score: number) {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-amber-500";
  return "bg-red-500";
}

const URGENCY_STYLES: Record<TopAction["urgency"], { border: string; badge: string; label: string }> = {
  urgent: { border: "border-l-red-500", badge: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400", label: "Urgent" },
  recommended: { border: "border-l-amber-500", badge: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", label: "Recommended" },
  consider: { border: "border-l-blue-500", badge: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", label: "Consider" },
};

const CONFIDENCE_STYLES: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string }> = {
  high: { icon: CheckCircle2, color: "text-green-600 dark:text-green-400" },
  medium: { icon: Info, color: "text-amber-600 dark:text-amber-400" },
  low: { icon: AlertTriangle, color: "text-muted-foreground" },
};

const SUGGESTED_QUESTIONS = [
  "How diversified am I?",
  "What should I buy?",
  "How is my portfolio performing?",
  "What are my biggest risks?",
];

// --- Health Score Section ---
function HealthScoreSection({ data }: { data: FullAdviceResponse["health_score"] }) {
  const score = data.overall_score;
  const color = scoreColor(score);
  const subScores = Object.entries(data.sub_scores);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-5 text-primary" />
          Portfolio Health Score
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col md:flex-row items-center gap-8">
          {/* Circular gauge */}
          <div className="relative size-32 shrink-0">
            <svg viewBox="0 0 36 36" className="size-32 -rotate-90">
              <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" className="text-muted/20" strokeWidth="3" />
              <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" className={color} strokeWidth="3"
                strokeDasharray={`${score} 100`} strokeLinecap="round" />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-3xl font-bold">{score}</span>
          </div>

          {/* Summary + sub-scores */}
          <div className="flex-1 w-full space-y-4">
            <p className="text-sm text-muted-foreground">{data.summary}</p>
            <div className="space-y-2">
              {subScores.map(([category, info]) => (
                <div key={category} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="capitalize font-medium">{category}</span>
                    <span className="text-muted-foreground">{info.score}/100 ({info.item_count} items)</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted/30">
                    <div
                      className={`h-2 rounded-full transition-all ${scoreBgColor(info.score)}`}
                      style={{ width: `${info.score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// --- Top Actions Section ---
function TopActionsSection({ actions }: { actions: TopAction[] }) {
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Top Actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {actions.map((action, i) => {
          const style = URGENCY_STYLES[action.urgency];
          return (
            <Card key={i} className={`border-l-4 ${style.border}`}>
              <CardContent className="py-4 space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${style.badge}`}>
                    {style.label}
                  </span>
                </div>
                <p className="text-sm font-semibold">{action.action}</p>
                <p className="text-xs text-muted-foreground">{action.rationale}</p>
                <p className="text-xs font-medium text-primary">{action.impact}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// --- Recommendations Section ---
function RecommendationCard({ rec }: { rec: Recommendation }) {
  const [expanded, setExpanded] = useState(false);
  const conf = CONFIDENCE_STYLES[rec.confidence] ?? CONFIDENCE_STYLES.low;
  const ConfIcon = conf.icon;

  return (
    <Card>
      <CardContent className="py-4 space-y-3">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-[11px]">{rec.category.replace("_", " ")}</Badge>
            <span className="text-sm font-semibold">{rec.title}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <ConfIcon className={`size-3.5 ${conf.color}`} />
            <span className={`text-xs font-medium capitalize ${conf.color}`}>{rec.confidence}</span>
          </div>
        </div>

        <p className="text-xs text-muted-foreground">{rec.rationale}</p>
        <p className="text-xs font-medium text-primary">{rec.impact}</p>

        {rec.suggested_etfs.length > 0 && (
          <div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-primary hover:underline"
            >
              {expanded ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
              {expanded ? "Hide" : "Show"} {rec.suggested_etfs.length} suggested ETFs
            </button>

            {expanded && (
              <div className="mt-2 overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-1.5 pr-3 font-medium">Name</th>
                      <th className="pb-1.5 pr-3 font-medium">Ticker</th>
                      <th className="pb-1.5 pr-3 font-medium">ISIN</th>
                      <th className="pb-1.5 pr-3 font-medium">TER</th>
                      <th className="pb-1.5 font-medium">Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rec.suggested_etfs.map((etf, j) => (
                      <tr key={j} className="border-b border-border/50 last:border-0">
                        <td className="py-1.5 pr-3 font-medium">{etf.name}</td>
                        <td className="py-1.5 pr-3 text-muted-foreground">{etf.ticker}</td>
                        <td className="py-1.5 pr-3 text-muted-foreground font-mono text-[11px]">{etf.isin}</td>
                        <td className="py-1.5 pr-3">{etf.ter}</td>
                        <td className="py-1.5 text-muted-foreground">{etf.why}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RecommendationsSection({ recommendations }: { recommendations: Recommendation[] }) {
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">What to Buy</h2>
      <div className="space-y-3">
        {recommendations.map((rec, i) => (
          <RecommendationCard key={i} rec={rec} />
        ))}
      </div>
    </div>
  );
}

// --- Scenarios Section ---
function AllocationBar({ allocation }: { allocation: Record<string, number> }) {
  const entries = Object.entries(allocation).sort((a, b) => b[1] - a[1]);
  const colors = [
    "bg-blue-500", "bg-green-500", "bg-amber-500", "bg-red-500",
    "bg-purple-500", "bg-teal-500", "bg-pink-500", "bg-indigo-500",
    "bg-orange-500", "bg-cyan-500", "bg-lime-500",
  ];

  return (
    <div className="space-y-1.5">
      <div className="flex h-4 w-full overflow-hidden rounded-full">
        {entries.map(([sector, pct], i) => (
          <div
            key={sector}
            className={`${colors[i % colors.length]} transition-all`}
            style={{ width: `${pct}%` }}
            title={`${sector}: ${pct.toFixed(1)}%`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {entries.map(([sector, pct], i) => (
          <div key={sector} className="flex items-center gap-1 text-[11px]">
            <span className={`inline-block size-2 rounded-full ${colors[i % colors.length]}`} />
            <span className="text-muted-foreground">{sector} {pct.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScenarioCard({ scenario }: { scenario: Scenario }) {
  const metricLabels: Record<string, string> = {
    sector_hhi: "Sector HHI",
    sector_count: "Sectors",
    estimated_yield: "Est. Yield",
    estimated_volatility: "Est. Vol.",
  };

  const beforeMetrics = Object.entries(scenario.before.metrics);
  const afterMetrics = Object.entries(scenario.after.metrics);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{scenario.title}</CardTitle>
        <p className="text-xs text-muted-foreground">{scenario.description}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <p className={labelClasses}>Before</p>
            <AllocationBar allocation={scenario.before.allocation} />
          </div>
          <div className="space-y-2">
            <p className={labelClasses}>After</p>
            <AllocationBar allocation={scenario.after.allocation} />
          </div>
        </div>

        {beforeMetrics.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {beforeMetrics.map(([key, val]) => {
              const afterVal = afterMetrics.find(([k]) => k === key)?.[1];
              const label = metricLabels[key] ?? key;
              return (
                <div key={key} className="text-center space-y-0.5">
                  <p className="text-[11px] text-muted-foreground">{label}</p>
                  <div className="flex items-center justify-center gap-2 text-xs">
                    <span className="text-muted-foreground">{typeof val === "number" && val % 1 !== 0 ? val.toFixed(1) : val}</span>
                    <span className="text-muted-foreground/40">&rarr;</span>
                    <span className="font-medium">{afterVal !== undefined ? (typeof afterVal === "number" && afterVal % 1 !== 0 ? afterVal.toFixed(1) : afterVal) : "-"}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ScenariosSection({ scenarios }: { scenarios: Scenario[] }) {
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Portfolio Scenarios</h2>
      <div className="space-y-3">
        {scenarios.map((scenario, i) => (
          <ScenarioCard key={i} scenario={scenario} />
        ))}
      </div>
    </div>
  );
}

// --- Chat Section ---
function ChatSection({ portfolioId }: { portfolioId: number }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: (message: string) => sendAdviceChat(portfolioId, message),
    onSuccess: (data) => {
      const assistantMsg = data.messages?.find((m) => m.role === "assistant");
      setMessages((prev) => [...prev, { role: "assistant", content: assistantMsg?.content ?? "No response." }]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I could not process your question. Please try again." },
      ]);
    },
  });

  const handleSend = (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || chatMutation.isPending) return;
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    chatMutation.mutate(message);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-5 text-primary" />
          Ask AI About Your Portfolio
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Messages */}
        {messages.length > 0 && (
          <div className="max-h-80 overflow-y-auto space-y-3 rounded-lg border border-border/50 p-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {chatMutation.isPending && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-xl px-3 py-2 text-sm">
                  <span className="inline-flex gap-1">
                    <span className="animate-pulse">.</span>
                    <span className="animate-pulse [animation-delay:200ms]">.</span>
                    <span className="animate-pulse [animation-delay:400ms]">.</span>
                  </span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Suggested questions */}
        <div className="flex flex-wrap gap-2">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              disabled={chatMutation.isPending}
              className="rounded-full border border-border/60 px-3 py-1 text-xs text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <Input
            placeholder="Ask a question about your portfolio..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={chatMutation.isPending}
          />
          <Button
            size="icon"
            onClick={() => handleSend()}
            disabled={!input.trim() || chatMutation.isPending}
          >
            <Send className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// --- Main Page ---
export default function AdvicePage() {
  const { selected } = usePortfolio();

  const {
    data,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["full-advice", selected?.id],
    queryFn: () => getFullAdvice(selected!.id),
    enabled: !!selected,
    staleTime: 5 * 60 * 1000,
    refetchInterval: (query) =>
      query.state.data?.has_pending_analysis ? 10_000 : false,
  });

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Sparkles className="size-12 text-muted-foreground opacity-40" />
        <p className="text-muted-foreground">Select a portfolio to view AI advice.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="animate-pulse bg-muted rounded-xl h-40" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-destructive">
          Failed to load AI advice. Please try again.
        </p>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="p-6 space-y-6">
      {/* Section 1: Health Score */}
      <HealthScoreSection data={data.health_score} />

      {/* Section 2: Top Actions */}
      {data.top_actions.length > 0 && (
        <TopActionsSection actions={data.top_actions} />
      )}

      {/* Section 3: Recommendations */}
      {data.recommendations.length > 0 && (
        <RecommendationsSection recommendations={data.recommendations} />
      )}

      {/* Section 4: Scenarios */}
      {data.scenarios.length > 0 && (
        <ScenariosSection scenarios={data.scenarios} />
      )}

      {/* Section 5: AI Chat */}
      <ChatSection portfolioId={selected.id} />

      {/* Section 6: Disclaimer */}
      {data.disclaimer && (
        <p className="text-xs text-muted-foreground">
          <strong>Important:</strong> {data.disclaimer.replace(/^Important:\s*/i, "")}
        </p>
      )}
    </div>
  );
}
