"use client";
import React, { useState } from "react";
import { motion } from "framer-motion"
import { FileText, ExternalLink, X, ChevronDown, ChevronUp, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

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

interface SourceDocumentsProps {
  context: ContextItem[]
  className?: string
}

interface DocumentChunkModalProps {
  chunk: ContextItem
  isOpen: boolean
  onClose: () => void
}

// Helper function to format filing date
const formatFilingDate = (dateString: string): string => {
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  } catch {
    return dateString
  }
}

// Helper function to get confidence level based on score
const getConfidenceLevel = (score: number): { level: string; color: string } => {
  if (score >= 0.8) return { level: "High", color: "text-green-600 dark:text-green-400" }
  if (score >= 0.6) return { level: "Medium", color: "text-yellow-600 dark:text-yellow-400" }
  return { level: "Low", color: "text-red-600 dark:text-red-400" }
}

function DocumentChunkModal({ chunk, isOpen, onClose }: DocumentChunkModalProps) {
  const formattedDate = formatFilingDate(chunk.filing_date)
  const confidence = getConfidenceLevel(chunk.score)

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] dark:bg-[#1a1d23] dark:border-gray-800">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3 text-slate-800 dark:text-gray-100">
            <div className="bg-blue-100 dark:bg-blue-900/30 p-2 rounded-lg">
              <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span>
                  {chunk.form} - {chunk.ticker}
                </span>
                <Badge variant="outline" className="text-xs">
                  Chunk {chunk.chunk_index}
                </Badge>
              </div>
              <div className="text-sm font-normal text-slate-500 dark:text-gray-400 mt-1">
                Filed: {formattedDate} • CIK: {chunk.cik} • Accession: {chunk.accession}
              </div>
            </div>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Confidence Score */}
          <div className="flex items-center gap-2 p-3 bg-slate-50 dark:bg-gray-800/50 rounded-lg">
            <Info className="h-4 w-4 text-slate-500 dark:text-gray-400" />
            <span className="text-sm text-slate-600 dark:text-gray-300">Relevance Score:</span>
            <span className={cn("text-sm font-medium", confidence.color)}>
              {(chunk.score * 100).toFixed(1)}% ({confidence.level})
            </span>
          </div>

          {/* Document Content */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-slate-700 dark:text-gray-300">Document Content:</h4>
            <ScrollArea className="h-[400px] w-full rounded-md border border-slate-200 dark:border-gray-700 p-4">
              <div className="text-sm text-slate-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                {chunk.text}
              </div>
            </ScrollArea>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-gray-700">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(chunk.url, "_blank")}
              className="flex items-center gap-2"
            >
              <ExternalLink className="h-4 w-4" />
              View Full Filing
            </Button>
            <Button variant="outline" size="sm" onClick={onClose}>
              <X className="h-4 w-4 mr-2" />
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function SourceDocuments({ context, className }: SourceDocumentsProps) {
  const [selectedChunk, setSelectedChunk] = useState<ContextItem | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)

  if (!context || context.length === 0) {
    return null
  }

  // Group chunks by document (ticker + filing_date)
  const groupedSources = context.reduce(
    (acc, chunk) => {
      const key = `${chunk.ticker}-${chunk.filing_date}-${chunk.form}`
      if (!acc[key]) {
        acc[key] = {
          ticker: chunk.ticker,
          filing_date: chunk.filing_date,
          accession: chunk.accession,
          form: chunk.form,
          url: chunk.url,
          cik: chunk.cik,
          chunks: [],
        }
      }
      acc[key].chunks.push(chunk)
      return acc
    },
    {} as Record<
      string,
      {
        ticker: string
        filing_date: string
        accession: string
        form: string
        url: string
        cik: string
        chunks: ContextItem[]
      }
    >,
  )

  const sources = Object.values(groupedSources)
  const displayedSources = isExpanded ? sources : sources.slice(0, 3)
  const hasMoreSources = sources.length > 3

  const handleChunkClick = (chunk: ContextItem) => {
    setSelectedChunk(chunk)
    setIsModalOpen(true)
  }

  const handleModalClose = () => {
    setIsModalOpen(false)
    setSelectedChunk(null)
  }

  return (
    <div className={cn("mt-3 space-y-2", className)}>
      <div className="flex items-center gap-2">
        <FileText className="h-4 w-4 text-slate-500 dark:text-gray-400" />
        <span className="text-xs font-medium text-slate-600 dark:text-gray-400">Sources:</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {displayedSources.map((source, index) => {
          const year = new Date(source.filing_date).getFullYear()

          return (
            <motion.div
              key={`${source.ticker}-${source.filing_date}-${source.form}`}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
            >
              {source.chunks.length === 1 ? (
                // Single chunk - direct click
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleChunkClick(source.chunks[0])}
                  className="h-auto py-1.5 px-3 text-xs hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200 hover:scale-105"
                >
                  <div className="flex items-center gap-1.5">
                    <FileText className="h-3 w-3" />
                    <span className="font-medium">
                      {source.form} {source.ticker} {year}
                    </span>
                  </div>
                </Button>
              ) : (
                // Multiple chunks - show dropdown or modal with chunk selection
                <div className="relative">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleChunkClick(source.chunks[0])} // Default to first chunk
                    className="h-auto py-1.5 px-3 text-xs hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200 hover:scale-105"
                  >
                    <div className="flex items-center gap-1.5">
                      <FileText className="h-3 w-3" />
                      <span className="font-medium">
                        {source.form} {source.ticker} {year}
                      </span>
                      <Badge variant="secondary" className="text-[10px] px-1 py-0">
                        {source.chunks.length}
                      </Badge>
                    </div>
                  </Button>
                </div>
              )}
            </motion.div>
          )
        })}

        {hasMoreSources && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-auto py-1.5 px-2 text-xs text-slate-500 dark:text-gray-400 hover:text-slate-700 dark:hover:text-gray-200"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-3 w-3 mr-1" />
                Show Less
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3 mr-1" />+{sources.length - 3} more
              </>
            )}
          </Button>
        )}
      </div>

      {/* Modal for displaying chunk content */}
      {selectedChunk && <DocumentChunkModal chunk={selectedChunk} isOpen={isModalOpen} onClose={handleModalClose} />}
    </div>
  )
}
