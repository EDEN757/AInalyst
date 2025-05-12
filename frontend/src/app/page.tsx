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
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { ThemeToggle } from "@/components/theme-toggle"

interface ContextItem {
  ticker: string
  accession: string
  chunk_index: number
  filing_date: string
  score: number
  text: string
}

interface Message {
  role: "user" | "assistant"
  content: string
  context?: ContextItem[]
}

const sampleQuestions = [
  "What were Apple's revenue trends in the last fiscal year?",
  "Explain Microsoft's cloud strategy based on their financial reports",
  "What risks did Tesla identify in their most recent filing?",
  "Compare Amazon's and Walmart's gross margins",
]

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isFullScreen, setIsFullScreen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    // Add user message to chat
    const userMessage: Message = { role: "user", content: input }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      // Send request to the FastAPI backend
      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: input,
          k: 5,
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
          content: "Sorry, I encountered an error processing your request. Please try again.",
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSampleQuestion = (question: string) => {
    setInput(question)
  }

  const toggleFullScreen = () => {
    setIsFullScreen(!isFullScreen)
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white dark:from-gray-950 dark:to-black transition-colors duration-300">
      <div className="container mx-auto px-4 py-8">
        <header className="flex justify-between items-center mb-8">
          <div className="text-center flex-1">
            <h1 className="text-3xl font-bold text-blue-800 dark:text-gray-300 mb-2">AInalyst</h1>
            <p className="text-gray-600 dark:text-gray-500 max-w-2xl mx-auto">
              Your intelligent assistant for analyzing financial data of public companies.
            </p>
          </div>
          <ThemeToggle />
        </header>

        <div className={`grid grid-cols-1 ${isFullScreen ? "" : "lg:grid-cols-3"} gap-8 transition-all duration-300`}>
          <div className={`${isFullScreen ? "col-span-full" : "lg:col-span-2"}`}>
            <Card className="w-full h-[70vh] flex flex-col shadow-lg border-blue-100 dark:border-gray-800 dark:bg-gray-900">
              <CardHeader className="bg-white dark:bg-gray-900 border-b border-blue-100 dark:border-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="bg-blue-600 dark:bg-gray-700 p-1.5 rounded-lg">
                      <Bot className="h-5 w-5 text-white dark:text-gray-300" />
                    </div>
                    <CardTitle className="dark:text-gray-300">AInalyst Chat</CardTitle>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="bg-blue-50 dark:bg-gray-800 dark:text-gray-400">
                      Financial AI
                    </Badge>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={toggleFullScreen}
                      className="border-blue-200 dark:border-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                    >
                      {isFullScreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                      <span className="sr-only">Toggle fullscreen</span>
                    </Button>
                  </div>
                </div>
              </CardHeader>

              <ScrollArea className="flex-1 p-4 h-full overflow-hidden dark:bg-gray-900">
                <div className="space-y-4 pb-4">
                  {messages.length === 0 ? (
                    <div className="text-center text-gray-500 dark:text-gray-500 my-12">
                      <div className="bg-blue-100 dark:bg-gray-800 p-3 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                        <Bot className="h-8 w-8 text-blue-600 dark:text-gray-400" />
                      </div>
                      <p className="text-xl font-medium mb-2 dark:text-gray-300">Welcome to AInalyst</p>
                      <p className="text-sm text-gray-500 dark:text-gray-500 max-w-md mx-auto">
                        Ask me anything about financial documents and public companies. I'll analyze the data and
                        provide insights.
                      </p>
                    </div>
                  ) : (
                    messages.map((message, index) => (
                      <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`max-w-[80%] rounded-lg p-3 break-words ${
                            message.role === "user"
                              ? "bg-blue-600 dark:bg-gray-700 text-white shadow-sm"
                              : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-300 shadow-sm"
                          }`}
                          style={{ wordBreak: "break-word", maxWidth: "80%" }}
                        >
                          <div className="flex items-start gap-2">
                            {message.role === "assistant" && (
                              <div className="bg-blue-100 dark:bg-gray-700 p-1 rounded-md mt-0.5">
                                <Bot className="h-4 w-4 text-blue-600 dark:text-gray-400" />
                              </div>
                            )}
                            {message.role === "user" && (
                              <div className="bg-blue-500 dark:bg-gray-600 p-1 rounded-md mt-0.5">
                                <User className="h-4 w-4 text-white dark:text-gray-300" />
                              </div>
                            )}
                            <div className="overflow-hidden w-full">
                              <p
                                className="whitespace-pre-wrap overflow-wrap-anywhere overflow-hidden"
                                style={{ maxWidth: "100%" }}
                              >
                                {message.content}
                              </p>
                              {message.context && (
                                <div className="mt-2 text-xs opacity-70">
                                  <p className="font-semibold">{message.role === "user" ? "" : "Sources:"}</p>
                                  {message.role === "assistant" && (
                                    <ul className="list-disc pl-4 mt-1">
                                      {message.context.slice(0, 3).map((item, idx) => (
                                        <li key={idx}>
                                          {item.ticker} ({item.filing_date})
                                        </li>
                                      ))}
                                      {message.context.length > 3 && (
                                        <li>+ {message.context.length - 3} more sources</li>
                                      )}
                                    </ul>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="max-w-[80%] rounded-lg p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-300 shadow-sm">
                        <div className="flex items-center gap-2">
                          <div className="bg-blue-100 dark:bg-gray-700 p-1 rounded-md">
                            <Bot className="h-4 w-4 text-blue-600 dark:text-gray-400" />
                          </div>
                          <div className="flex space-x-1">
                            <div
                              className="h-2 w-2 bg-blue-400 dark:bg-gray-500 rounded-full animate-bounce"
                              style={{ animationDelay: "0ms" }}
                            ></div>
                            <div
                              className="h-2 w-2 bg-blue-400 dark:bg-gray-500 rounded-full animate-bounce"
                              style={{ animationDelay: "150ms" }}
                            ></div>
                            <div
                              className="h-2 w-2 bg-blue-400 dark:bg-gray-500 rounded-full animate-bounce"
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

              <CardFooter className="border-t p-4 bg-gray-50 dark:bg-gray-950 dark:border-gray-800">
                <form onSubmit={handleSubmit} className="flex w-full gap-2">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about financial documents..."
                    className="flex-1 border-blue-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 focus-visible:ring-blue-500 dark:focus-visible:ring-gray-600"
                    disabled={isLoading}
                  />
                  <Button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="bg-blue-600 hover:bg-blue-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              </CardFooter>
            </Card>
          </div>

          {!isFullScreen && (
            <div className="space-y-6">
              <Card className="shadow-md border-blue-100 dark:border-gray-800 dark:bg-gray-900">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2 dark:text-gray-300">
                    <HelpCircle className="h-5 w-5 text-blue-600 dark:text-gray-400" />
                    Try asking about
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {sampleQuestions.map((question, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        className="w-full justify-start text-left h-auto py-3 border-blue-100 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-gray-800 hover:text-blue-700 dark:hover:text-gray-300 dark:text-gray-400"
                        onClick={() => handleSampleQuestion(question)}
                      >
                        <span className="truncate">{question}</span>
                        <ChevronRight className="h-4 w-4 ml-auto flex-shrink-0" />
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-md border-blue-100 dark:border-gray-800 dark:bg-gray-900">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2 dark:text-gray-300">
                    <FileText className="h-5 w-5 text-blue-600 dark:text-gray-400" />
                    About AInalyst
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600 dark:text-gray-500 mb-4">
                    AInalyst uses advanced AI to analyze financial documents and provide insights about public
                    companies.
                  </p>
                  <div className="space-y-3">
                    <div className="flex items-start gap-2">
                      <BarChart3 className="h-5 w-5 text-blue-600 dark:text-gray-400 mt-0.5" />
                      <div>
                        <h3 className="font-medium dark:text-gray-300">Financial Analysis</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-500">
                          Get insights on company performance and metrics
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <TrendingUp className="h-5 w-5 text-blue-600 dark:text-gray-400 mt-0.5" />
                      <div>
                        <h3 className="font-medium dark:text-gray-300">Market Trends</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-500">
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

        <footer className="mt-12 text-center text-sm text-gray-500 dark:text-gray-600">
          <p>AInalyst © {new Date().getFullYear()} | Powered by AI analysis of financial documents</p>
        </footer>
      </div>
    </div>
  )
}
