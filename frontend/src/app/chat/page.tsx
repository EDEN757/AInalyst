"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import {
  Send,
  Bot,
  User,
  FileText,
  BarChart3,
  TrendingUp,
  HelpCircle,
  ChevronRight,
  Maximize2,
  Minimize2,
  ArrowLeft,
  Copy,
  CheckCheck,
  Settings,
  Eye,
  EyeOff,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { ThemeToggle } from "@/components/theme-toggle"
import { SourceDocuments } from "@/components/source-documents"
import { cn } from "@/lib/utils"
import Link from "next/link"

// Base URL for backend API: overridden by Vercel env var in production
const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

interface ContextItem {
  ticker: string
  accession: string
  chunk_index: number
  filing_date: string
  score: number
  text: string
  form: string
  url: string
  cik: string
}

interface Message {
  role: "user" | "assistant"
  content: string
  context?: ContextItem[]
}

interface ApiConfig {
  apiKey: string
  chatModel: string
}

const sampleQuestions = [
  "What were Apple's revenue trends in the last fiscal year?",
  "Explain Microsoft's cloud strategy based on their financial reports",
  "What risks did Tesla identify in their most recent filing?",
  "Compare Amazon's and Walmart's gross margins",
]

const AVAILABLE_MODELS = [{ value: "gpt-4.1-mini-2025-04-14", label: "gpt-4.1-mini-2025-04-14" }]

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isFullScreen, setIsFullScreen] = useState(false)
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)
  const [apiConfig, setApiConfig] = useState<ApiConfig>({ apiKey: "", chatModel: "" })
  const [tempConfig, setTempConfig] = useState<ApiConfig>({ apiKey: "", chatModel: "" })
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
    if (!showConfigModal && apiConfig.apiKey && apiConfig.chatModel) {
      inputRef.current?.focus()
    }
  }, [messages, showConfigModal, apiConfig])

  // Load config from sessionStorage on mount
  useEffect(() => {
    const savedConfig = sessionStorage.getItem("ainalyst-config")
    if (savedConfig) {
      try {
        const config = JSON.parse(savedConfig) as ApiConfig
        if (config.apiKey && config.chatModel) {
          setApiConfig(config)
          setTempConfig(config)
          return
        }
      } catch (error) {
        console.error("Failed to parse saved config:", error)
      }
    }
    // Show modal if no valid config found
    setShowConfigModal(true)
    setTempConfig({ apiKey: "", chatModel: AVAILABLE_MODELS[0].value })
  }, [])

  const handleConfigSubmit = () => {
    if (!tempConfig.apiKey.trim()) {
      return // Don't close modal if API key is empty
    }

    const newConfig = {
      apiKey: tempConfig.apiKey.trim(),
      chatModel: tempConfig.chatModel || AVAILABLE_MODELS[0].value,
    }

    setApiConfig(newConfig)
    sessionStorage.setItem("ainalyst-config", JSON.stringify(newConfig))
    setShowConfigModal(false)
  }

  const handleOpenSettings = () => {
    setTempConfig({ ...apiConfig })
    setShowConfigModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !apiConfig.apiKey || !apiConfig.chatModel) return

    // Add user message to chat
    const userMessage: Message = { role: "user", content: input }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      // Send request to the FastAPI backend with API key and model
      const response = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: input,
          k: 5,
          api_key: apiConfig.apiKey,
          chat_model: apiConfig.chatModel,
        }),
      })

      if (!response.ok) {
        throw new Error("Failed to get response")
      }

      const data = await response.json()

      // Add assistant message with context
      const assistantMessage: Message = {
        role: "assistant",
        content: data.answer,
        context: data.context,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Error:", error)
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error processing your request. Please check your API key and try again.",
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSampleQuestion = (question: string) => {
    setInput(question)
    inputRef.current?.focus()
  }

  const toggleFullScreen = () => {
    setIsFullScreen(!isFullScreen)
  }

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(index)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const isConfigured = apiConfig.apiKey && apiConfig.chatModel

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-gray-950 dark:to-[#0d1117] transition-colors duration-300 font-sans">
      <div className="w-full px-5vw py-6 h-[calc(100vh-2rem)]">
        <header className="flex justify-between items-center mb-6 max-w-[1600px] mx-auto">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button
                variant="ghost"
                size="icon"
                className="text-slate-700 dark:text-gray-300 hover:bg-slate-100 dark:hover:bg-gray-800"
              >
                <ArrowLeft className="h-5 w-5" />
                <span className="sr-only">Back to intro</span>
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-slate-800 dark:text-gray-100">AInalyst</h1>
              <p className="text-slate-500 dark:text-gray-400 text-sm">
                Your intelligent assistant for analyzing financial data
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={handleOpenSettings}
              className="border-slate-200 text-slate-600 hover:text-slate-900 dark:border-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              title="Settings"
            >
              <Settings className="h-4 w-4" />
              <span className="sr-only">Settings</span>
            </Button>
            <ThemeToggle />
          </div>
        </header>

        <div
          className={`grid ${
            isFullScreen ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-[1fr_350px]"
          } gap-6 h-[calc(100%-4rem)] max-w-[1600px] mx-auto`}
        >
          <div className="h-full flex flex-col">
            <Card className="flex-1 flex flex-col shadow-md border-slate-200 dark:border-gray-800 dark:bg-[#1a1d23] overflow-hidden">
              <CardHeader className="bg-white dark:bg-[#1a1d23] border-b border-slate-100 dark:border-gray-800 py-4 px-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="bg-blue-600 dark:bg-blue-700 p-1.5 rounded-lg">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                    <CardTitle className="text-xl font-semibold text-slate-800 dark:text-gray-100">Chat</CardTitle>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-xs",
                        isConfigured
                          ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800"
                          : "bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800",
                      )}
                    >
                      {isConfigured ? "Configured" : "Setup Required"}
                    </Badge>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={toggleFullScreen}
                      className="border-slate-200 text-slate-600 hover:text-slate-900 dark:border-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                      {isFullScreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                      <span className="sr-only">Toggle fullscreen</span>
                    </Button>
                  </div>
                </div>
              </CardHeader>

              <ScrollArea className="flex-1 p-6 h-full overflow-hidden dark:bg-[#1a1d23]">
                <div className="space-y-6 pb-4 w-full max-w-[1200px] mx-auto">
                  {messages.length === 0 ? (
                    <div className="text-center text-slate-500 dark:text-gray-400 my-12">
                      <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-full w-20 h-20 mx-auto mb-6 flex items-center justify-center">
                        <Bot className="h-10 w-10 text-blue-600 dark:text-blue-400" />
                      </div>
                      <p className="text-2xl font-semibold mb-3 text-slate-700 dark:text-gray-200">
                        Welcome to AInalyst
                      </p>
                      <p className="text-slate-500 dark:text-gray-400 max-w-md mx-auto">
                        {isConfigured
                          ? "Ask me anything about financial documents and public companies. I'll analyze the data and provide insights to help with your financial research."
                          : "Please configure your API settings to start chatting."}
                      </p>
                    </div>
                  ) : (
                    messages.map((message, index) => (
                      <div
                        key={index}
                        className={cn("group flex flex-col", message.role === "user" ? "items-end" : "items-start")}
                      >
                        <div
                          className={cn(
                            "rounded-2xl p-4 break-words relative",
                            message.role === "user"
                              ? "bg-blue-600 dark:bg-blue-700 text-white ml-auto"
                              : "bg-white dark:bg-[#252930] border border-slate-100 dark:border-gray-800 text-slate-800 dark:text-gray-200 mr-auto",
                            "max-w-[70%] md:max-w-[65%]",
                          )}
                        >
                          <div className="flex items-start gap-3">
                            {message.role === "assistant" && (
                              <div className="bg-blue-100 dark:bg-blue-900/30 p-1.5 rounded-md mt-0.5 flex-shrink-0">
                                <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                              </div>
                            )}
                            {message.role === "user" && (
                              <div className="bg-blue-500 dark:bg-blue-600 p-1.5 rounded-md mt-0.5 flex-shrink-0 order-last">
                                <User className="h-4 w-4 text-white" />
                              </div>
                            )}
                            <div className="overflow-hidden w-full">
                              <p className="whitespace-pre-wrap overflow-wrap-anywhere overflow-hidden text-[15px] leading-relaxed">
                                {message.content}
                              </p>
                            </div>
                          </div>

                          {/* Copy button */}
                          <Button
                            variant="ghost"
                            size="icon"
                            className={cn(
                              "absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity",
                              message.role === "user"
                                ? "text-blue-200 hover:text-white hover:bg-blue-500"
                                : "text-slate-400 hover:text-slate-700 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-slate-100 dark:hover:bg-gray-800",
                            )}
                            onClick={() => copyToClipboard(message.content, index)}
                          >
                            {copiedIndex === index ? <CheckCheck className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                            <span className="sr-only">Copy message</span>
                          </Button>
                        </div>

                        {/* Source Documents - only for assistant messages */}
                        {message.role === "assistant" && message.context && (
                          <div className="max-w-[70%] md:max-w-[65%] mr-auto">
                            <SourceDocuments context={message.context} />
                          </div>
                        )}
                      </div>
                    ))
                  )}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="max-w-[70%] md:max-w-[65%] rounded-2xl p-4 bg-white dark:bg-[#252930] border border-slate-100 dark:border-gray-800 text-slate-800 dark:text-gray-200">
                        <div className="flex items-center gap-3">
                          <div className="bg-blue-100 dark:bg-blue-900/30 p-1.5 rounded-md">
                            <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                          </div>
                          <div className="flex space-x-2">
                            <div
                              className="h-2.5 w-2.5 bg-blue-400 dark:bg-blue-500 rounded-full animate-bounce"
                              style={{ animationDelay: "0ms" }}
                            ></div>
                            <div
                              className="h-2.5 w-2.5 bg-blue-400 dark:bg-blue-500 rounded-full animate-bounce"
                              style={{ animationDelay: "150ms" }}
                            ></div>
                            <div
                              className="h-2.5 w-2.5 bg-blue-400 dark:bg-blue-500 rounded-full animate-bounce"
                              style={{ animationDelay: "300ms" }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              <CardFooter className="border-t p-4 bg-slate-50 dark:bg-[#20232a] dark:border-gray-800 shadow-[0_-1px_2px_rgba(0,0,0,0.03)] dark:shadow-none">
                <form onSubmit={handleSubmit} className="flex w-full gap-3 items-center">
                  <Input
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={
                      isConfigured ? "Ask about financial documents..." : "Configure API settings to start chatting..."
                    }
                    className="flex-1 border-slate-200 bg-white dark:border-gray-700 dark:bg-[#2d333b] dark:text-gray-200 focus-visible:ring-blue-500 dark:focus-visible:ring-blue-600 h-12 px-4 text-base"
                    disabled={isLoading || !isConfigured}
                  />
                  <Button
                    type="submit"
                    disabled={isLoading || !input.trim() || !isConfigured}
                    className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 h-12 px-5"
                  >
                    <Send className="h-5 w-5 mr-2" />
                    <span>Send</span>
                  </Button>
                </form>
              </CardFooter>
            </Card>
          </div>

          {!isFullScreen && (
            <div className="space-y-6">
              <Card className="shadow-sm border-slate-200 dark:border-gray-800 dark:bg-[#1a1d23] overflow-hidden hover:shadow-md transition-shadow duration-200">
                <CardHeader className="py-4 px-5">
                  <CardTitle className="text-base flex items-center gap-2 text-slate-800 dark:text-gray-100">
                    <HelpCircle className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    Try asking about
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-5">
                  <div className="space-y-2.5">
                    {sampleQuestions.map((question, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        className="w-full justify-start text-left h-auto py-3 px-4 border-slate-200 dark:border-gray-700 hover:bg-slate-50 dark:hover:bg-gray-800 hover:text-blue-700 dark:hover:text-blue-400 text-slate-700 dark:text-gray-300 text-sm font-medium"
                        onClick={() => handleSampleQuestion(question)}
                        disabled={!isConfigured}
                      >
                        <span className="truncate">{question}</span>
                        <ChevronRight className="h-4 w-4 ml-auto flex-shrink-0 text-slate-400 dark:text-gray-500" />
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-sm border-slate-200 dark:border-gray-800 dark:bg-[#1a1d23] overflow-hidden hover:shadow-md transition-shadow duration-200">
                <CardHeader className="py-4 px-5">
                  <CardTitle className="text-base flex items-center gap-2 text-slate-800 dark:text-gray-100">
                    <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    About AInalyst
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-5">
                  <p className="text-sm text-slate-600 dark:text-gray-400 mb-4 leading-relaxed">
                    AInalyst uses advanced AI to analyze financial documents and provide insights about public
                    companies.
                  </p>
                  <div className="space-y-4">
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 dark:bg-gray-800/50">
                      <BarChart3 className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                      <div>
                        <h3 className="font-medium text-slate-800 dark:text-gray-200 text-sm">Financial Analysis</h3>
                        <p className="text-xs text-slate-500 dark:text-gray-400 mt-1">
                          Get insights on company performance and metrics
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 dark:bg-gray-800/50">
                      <TrendingUp className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                      <div>
                        <h3 className="font-medium text-slate-800 dark:text-gray-200 text-sm">Market Trends</h3>
                        <p className="text-xs text-slate-500 dark:text-gray-400 mt-1">
                          Understand market positioning and competitive landscape
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        <footer className="mt-6 text-center text-xs text-slate-400 dark:text-gray-600 max-w-[1600px] mx-auto">
          <p>AInalyst © {new Date().getFullYear()} | Powered by AI analysis of financial documents</p>
        </footer>
      </div>

      {/* API Configuration Modal */}
      <Dialog open={showConfigModal} onOpenChange={() => {}}>
        <DialogContent className="sm:max-w-md dark:bg-[#1a1d23] dark:border-gray-800">
          <DialogHeader>
            <DialogTitle className="text-slate-800 dark:text-gray-100">Configure API Settings</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="api-key" className="text-sm font-medium text-slate-700 dark:text-gray-300">
                OpenAI API Key
              </Label>
              <div className="relative">
                <Input
                  id="api-key"
                  type={showApiKey ? "text" : "password"}
                  value={tempConfig.apiKey}
                  onChange={(e) => setTempConfig({ ...tempConfig, apiKey: e.target.value })}
                  placeholder="sk-..."
                  className="pr-10 border-slate-200 dark:border-gray-700 dark:bg-[#2d333b] dark:text-gray-200"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3 text-slate-400 hover:text-slate-600 dark:text-gray-500 dark:hover:text-gray-300"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  <span className="sr-only">{showApiKey ? "Hide" : "Show"} API key</span>
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="model" className="text-sm font-medium text-slate-700 dark:text-gray-300">
                Model
              </Label>
              <Select
                value={tempConfig.chatModel}
                onValueChange={(value) => setTempConfig({ ...tempConfig, chatModel: value })}
              >
                <SelectTrigger className="border-slate-200 dark:border-gray-700 dark:bg-[#2d333b] dark:text-gray-200">
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent className="dark:bg-[#2d333b] dark:border-gray-700">
                  {AVAILABLE_MODELS.map((model) => (
                    <SelectItem
                      key={model.value}
                      value={model.value}
                      className="dark:text-gray-200 dark:focus:bg-gray-700"
                    >
                      {model.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button
              onClick={handleConfigSubmit}
              disabled={!tempConfig.apiKey.trim()}
              className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600"
            >
              Save Configuration
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
