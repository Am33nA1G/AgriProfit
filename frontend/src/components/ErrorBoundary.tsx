"use client"

import React, { Component, ErrorInfo, ReactNode } from "react"
import { AlertTriangle, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
    children: ReactNode
    fallback?: ReactNode
    onReset?: () => void
}

interface State {
    hasError: boolean
    error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
    }

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error }
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Uncaught error:", error, errorInfo)
    }

    private handleReset = () => {
        this.setState({ hasError: false, error: null })
        this.props.onReset?.()
    }

    public render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback
            }

            return (
                <div className="flex items-center justify-center min-h-[400px] p-4">
                    <Card className="max-w-md w-full">
                        <CardHeader className="text-center">
                            <div className="mx-auto mb-4 p-3 rounded-full bg-destructive/10 w-fit">
                                <AlertTriangle className="h-8 w-8 text-destructive" />
                            </div>
                            <CardTitle>Something went wrong</CardTitle>
                        </CardHeader>
                        <CardContent className="text-center">
                            <p className="text-muted-foreground">
                                We encountered an unexpected error. Please try refreshing the page.
                            </p>
                            {process.env.NODE_ENV === "development" && this.state.error && (
                                <pre className="mt-4 p-3 bg-muted rounded-md text-xs text-left overflow-auto max-h-32">
                                    {this.state.error.message}
                                </pre>
                            )}
                        </CardContent>
                        <CardFooter className="flex justify-center gap-3">
                            <Button variant="outline" onClick={() => window.location.reload()}>
                                <RefreshCw className="h-4 w-4 mr-2" />
                                Refresh Page
                            </Button>
                            <Button onClick={this.handleReset}>
                                Try Again
                            </Button>
                        </CardFooter>
                    </Card>
                </div>
            )
        }

        return this.props.children
    }
}

// Functional wrapper for easier use
interface ErrorBoundaryWrapperProps {
    children: ReactNode
    fallback?: ReactNode
    onReset?: () => void
}

export function WithErrorBoundary({ children, fallback, onReset }: ErrorBoundaryWrapperProps) {
    return (
        <ErrorBoundary fallback={fallback} onReset={onReset}>
            {children}
        </ErrorBoundary>
    )
}

// Error fallback component for inline use
interface ErrorFallbackProps {
    error?: Error | string | null
    onRetry?: () => void
    title?: string
    description?: string
}

export function ErrorFallback({
    error,
    onRetry,
    title = "Failed to load",
    description = "Something went wrong while loading this content.",
}: ErrorFallbackProps) {
    return (
        <Card className="p-8 text-center">
            <div className="flex flex-col items-center">
                <div className="p-3 rounded-full bg-destructive/10 mb-4">
                    <AlertTriangle className="h-6 w-6 text-destructive" />
                </div>
                <h3 className="font-semibold text-lg mb-2">{title}</h3>
                <p className="text-muted-foreground mb-4">{description}</p>
                {process.env.NODE_ENV === "development" && error && (
                    <pre className="mb-4 p-2 bg-muted rounded text-xs text-left max-w-full overflow-auto">
                        {typeof error === "string" ? error : error.message}
                    </pre>
                )}
                {onRetry && (
                    <Button onClick={onRetry}>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Try Again
                    </Button>
                )}
            </div>
        </Card>
    )
}

export default ErrorBoundary
