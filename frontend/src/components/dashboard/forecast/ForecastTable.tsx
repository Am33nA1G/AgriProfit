"use client"

import React from "react"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ForecastPoint } from "@/services/forecasts"
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react"

interface ForecastTableProps {
    data: ForecastPoint[]
    currentPrice: number
}

export function ForecastTable({ data, currentPrice }: ForecastTableProps) {
    return (
        <div className="rounded-md border max-h-[400px] overflow-auto">
            <div className="overflow-x-auto">
                <Table className="min-w-[600px]">
                    <TableHeader>
                        <TableRow>
                            <TableHead>Date</TableHead>
                            <TableHead className="text-right">Predicted Price</TableHead>
                            <TableHead className="text-right">Change</TableHead>
                            <TableHead className="text-center">Confidence</TableHead>
                            <TableHead className="text-center">Recommendation</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {data.map((point, index) => {
                            const change = point.predicted_price - currentPrice
                            const changePercent = (change / currentPrice) * 100

                            return (
                                <TableRow key={index}>
                                    <TableCell className="font-medium">
                                        {new Date(point.date).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}
                                    </TableCell>
                                    <TableCell className="text-right">
                                        ₹{point.predicted_price.toFixed(2)}
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <div className={`flex items-center justify-end gap-1 ${change > 0 ? "text-green-600" : change < 0 ? "text-red-600" : "text-muted-foreground"
                                            }`}>
                                            {change > 0 ? <ArrowUpRight className="h-4 w-4" /> : change < 0 ? <ArrowDownRight className="h-4 w-4" /> : <Minus className="h-4 w-4" />}
                                            {Math.abs(changePercent).toFixed(1)}%
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-center">
                                        <Badge variant={
                                            point.confidence === "HIGH" ? "default" :
                                                point.confidence === "MEDIUM" ? "secondary" : "outline"
                                        } className={
                                            point.confidence === "HIGH" ? "bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400" :
                                                point.confidence === "MEDIUM" ? "bg-yellow-100 text-yellow-800 hover:bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400" : ""
                                        }>
                                            {point.confidence}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-center">
                                        <Badge variant="outline" className={
                                            point.recommendation === "SELL" ? "border-green-500 text-green-600" :
                                                point.recommendation === "WAIT" ? "border-red-500 text-red-600" : ""
                                        }>
                                            {point.recommendation}
                                        </Badge>
                                    </TableCell>
                                </TableRow>
                            )
                        })}
                    </TableBody>
                </Table>
            </div>
        </div>
    )
}
