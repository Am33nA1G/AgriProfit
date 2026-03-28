"use client"

import { useEffect } from "react"
import { AlertTriangle, RefreshCw, Home } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string }
    reset: () => void
}) {
    useEffect(() => {
        // Log the error to an error reporting service
        console.error("Application error:", error)
    }, [error])

    return (
        <div className="min-h-screen bg-background flex items-center justify-center p-4">
            <Card className="max-w-lg w-full">
                <CardHeader className="text-center">
                    <div className="mx-auto mb-4 p-4 rounded-full bg-destructive/10 w-fit">
                        <AlertTriangle className="h-10 w-10 text-destructive" />
                    </div>
                    <CardTitle className="text-2xl">Something went wrong!</CardTitle>
                </CardHeader>
                <CardContent className="text-center">
                    <p className="text-muted-foreground mb-4">
                        We apologize for the inconvenience. An unexpected error has occurred.
                    </p>
                    {process.env.NODE_ENV === "development" && (
                        <div className="mt-4 p-4 bg-muted rounded-lg text-left">
                            <p className="text-sm font-mono text-destructive break-all">
                                {error.message}
                            </p>
                            {error.digest && (
                                <p className="text-xs text-muted-foreground mt-2">
                                    Error ID: {error.digest}
                                </p>
                            )}
                        </div>
                    )}
                </CardContent>
                <CardFooter className="flex justify-center gap-4">
                    <Button variant="outline" onClick={() => window.location.href = "/"}>
                        <Home className="h-4 w-4 mr-2" />
                        Go Home
                    </Button>
                    <Button onClick={reset}>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Try Again
                    </Button>
                </CardFooter>
            </Card>
        </div>
    )
}
