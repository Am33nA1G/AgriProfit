"use client"

import React, { useState } from "react"

interface EndpointResult {
    url: string
    status: number | null
    ok: boolean
    latency: number
    data: string
    error?: string
}

const ENDPOINTS = [
    { name: "Health", path: "/health", baseApi: false },
    { name: "Commodities", path: "/commodities/?limit=5", baseApi: true },
    { name: "Mandis", path: "/mandis/?limit=5", baseApi: true },
    { name: "Prices (Current)", path: "/prices/current?limit=5", baseApi: true },
    { name: "Analytics Dashboard", path: "/analytics/dashboard", baseApi: true },
    { name: "Analytics Summary", path: "/analytics/summary", baseApi: true },
    { name: "Top Commodities", path: "/analytics/top-commodities?limit=5", baseApi: true },
    { name: "Top Mandis", path: "/analytics/top-mandis?limit=5", baseApi: true },
    { name: "Commodities With Prices", path: "/commodities/with-prices?limit=5", baseApi: true },
    { name: "Commodity Categories", path: "/commodities/categories", baseApi: true },
    { name: "Mandi States", path: "/mandis/states", baseApi: true },
    { name: "Price History", path: "/prices/?limit=5", baseApi: true },
    { name: "Top Movers", path: "/prices/top-movers?limit=3", baseApi: true },
]

export default function ApiTestPage() {
    const [results, setResults] = useState<EndpointResult[]>([])
    const [testing, setTesting] = useState(false)
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1"
    const backendRoot = baseUrl.replace(/\/api\/v1$/, "")

    const testEndpoint = async (name: string, path: string, baseApi: boolean): Promise<EndpointResult> => {
        const url = baseApi ? `${baseUrl}${path}` : `${backendRoot}${path}`
        const start = performance.now()
        try {
            const response = await fetch(url, {
                method: "GET",
                headers: { "Content-Type": "application/json" },
            })
            const latency = Math.round(performance.now() - start)
            let data = ""
            try {
                const json = await response.json()
                data = JSON.stringify(json, null, 2).slice(0, 500)
                if (data.length >= 500) data += "\n... (truncated)"
            } catch {
                data = await response.text()
            }
            return { url, status: response.status, ok: response.ok, latency, data }
        } catch (err: unknown) {
            const latency = Math.round(performance.now() - start)
            const errorMsg = err instanceof Error ? err.message : "Unknown error"
            return { url, status: null, ok: false, latency, data: "", error: errorMsg }
        }
    }

    const runTests = async () => {
        setTesting(true)
        setResults([])
        const newResults: EndpointResult[] = []
        for (const ep of ENDPOINTS) {
            const result = await testEndpoint(ep.name, ep.path, ep.baseApi)
            newResults.push(result)
            setResults([...newResults])
        }
        setTesting(false)
    }

    const passCount = results.filter(r => r.ok).length
    const failCount = results.filter(r => !r.ok).length

    return (
        <div style={{ maxWidth: 900, margin: "0 auto", padding: 24, fontFamily: "monospace" }}>
            <h1 style={{ fontSize: 24, fontWeight: "bold", marginBottom: 8 }}>API Endpoint Diagnostic</h1>
            <p style={{ color: "#666", marginBottom: 16 }}>
                Base URL: <code style={{ background: "#f0f0f0", padding: "2px 6px", borderRadius: 4 }}>{baseUrl}</code>
            </p>

            <button
                onClick={runTests}
                disabled={testing}
                style={{
                    padding: "8px 20px",
                    background: testing ? "#999" : "#22c55e",
                    color: "white",
                    border: "none",
                    borderRadius: 6,
                    cursor: testing ? "not-allowed" : "pointer",
                    fontSize: 14,
                    fontWeight: "bold",
                    marginBottom: 24,
                }}
            >
                {testing ? "Testing..." : "Run All Tests"}
            </button>

            {results.length > 0 && (
                <div style={{ marginBottom: 16, fontSize: 14 }}>
                    <span style={{ color: "#22c55e", fontWeight: "bold" }}>{passCount} passed</span>
                    {" / "}
                    <span style={{ color: failCount > 0 ? "#ef4444" : "#666", fontWeight: "bold" }}>{failCount} failed</span>
                    {" / "}
                    <span>{ENDPOINTS.length} total</span>
                </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {ENDPOINTS.map((ep, i) => {
                    const result = results[i]
                    return (
                        <div key={ep.name} style={{
                            border: "1px solid #e0e0e0",
                            borderRadius: 8,
                            padding: 16,
                            background: result
                                ? result.ok ? "#f0fdf4" : "#fef2f2"
                                : "#f9fafb",
                        }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                                <strong>{ep.name}</strong>
                                {result && (
                                    <span style={{
                                        padding: "2px 8px",
                                        borderRadius: 4,
                                        fontSize: 12,
                                        fontWeight: "bold",
                                        background: result.ok ? "#22c55e" : "#ef4444",
                                        color: "white",
                                    }}>
                                        {result.status ?? "ERR"} - {result.latency}ms
                                    </span>
                                )}
                            </div>
                            <div style={{ fontSize: 12, color: "#666", marginBottom: result ? 8 : 0 }}>
                                {ep.baseApi ? baseUrl : backendRoot}{ep.path}
                            </div>
                            {result && (
                                <details style={{ fontSize: 12 }}>
                                    <summary style={{ cursor: "pointer", color: "#333" }}>
                                        {result.ok ? "Response preview" : result.error || "Error"}
                                    </summary>
                                    <pre style={{
                                        marginTop: 8,
                                        padding: 8,
                                        background: "#f3f4f6",
                                        borderRadius: 4,
                                        overflow: "auto",
                                        maxHeight: 200,
                                        fontSize: 11,
                                        whiteSpace: "pre-wrap",
                                    }}>
                                        {result.data || result.error || "No data"}
                                    </pre>
                                </details>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
