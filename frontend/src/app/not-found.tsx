import { FileQuestion, Home, ArrowLeft } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

export default function NotFound() {
    return (
        <div className="min-h-screen bg-background flex items-center justify-center p-4">
            <Card className="max-w-lg w-full text-center">
                <CardHeader>
                    <div className="mx-auto mb-4 p-4 rounded-full bg-muted w-fit">
                        <FileQuestion className="h-10 w-10 text-muted-foreground" />
                    </div>
                    <CardTitle className="text-2xl">Page Not Found</CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">
                        The page you're looking for doesn't exist or has been moved.
                    </p>
                </CardContent>
                <CardFooter className="flex justify-center gap-4">
                    <Button variant="outline" asChild>
                        <Link href="javascript:history.back()">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Go Back
                        </Link>
                    </Button>
                    <Button asChild>
                        <Link href="/dashboard">
                            <Home className="h-4 w-4 mr-2" />
                            Go to Dashboard
                        </Link>
                    </Button>
                </CardFooter>
            </Card>
        </div>
    )
}
