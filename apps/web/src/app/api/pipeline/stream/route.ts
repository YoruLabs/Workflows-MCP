import { NextRequest } from "next/server";
import { spawn } from "child_process";
import path from "path";
import fs from "fs/promises";

/**
 * SSE Streaming API for pipeline progress
 * Streams real-time progress updates as the Python script runs
 */
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { query, limit = 5, useApify = true } = body;

  if (!query) {
    return new Response(JSON.stringify({ error: "Query is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Resolve paths
  const projectRoot = path.resolve(process.cwd(), "../../");
  const scriptPath = path.join(projectRoot, "skills/apollo-clay-leads/scripts/run_pipeline.py");
  const outputPath = path.resolve(projectRoot, "../output/leads.json");

  // Create readable stream for SSE
  const encoder = new TextEncoder();
  
  const stream = new ReadableStream({
    async start(controller) {
      // Helper to send SSE event
      const sendEvent = (type: string, data: any) => {
        const event = `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
        controller.enqueue(encoder.encode(event));
      };

      try {
        // Send initial event
        sendEvent("progress", { step: "starting", message: "Starting pipeline..." });

        // Log the incoming query for debugging
        console.log("🔍 [Pipeline Stream] Query received:", query);
        console.log("📊 [Pipeline Stream] Limit:", limit);

        // Build command args
        const args = [
          scriptPath,
          "--query", query,
          "--limit", String(limit),
        ];
        if (useApify) args.push("--apify");

        // Spawn Python process
        const pythonProcess = spawn("python3", args, { cwd: projectRoot });

        // Parse stderr for progress (Python logging goes to stderr)
        pythonProcess.stderr.on("data", (data: Buffer) => {
          const lines = data.toString().split("\n");
          
          for (const line of lines) {
            if (!line.trim()) continue;
            
            // Parse step indicators from logs
            if (line.includes("STEP 1:")) {
              sendEvent("progress", { step: "ingest", message: "Fetching leads from LinkedIn..." });
            } else if (line.includes("Fetching from LinkedIn via Apify")) {
              sendEvent("progress", { step: "apify", message: "Searching LinkedIn via Apify..." });
            } else if (line.includes("Got") && line.includes("profiles from Apify")) {
              const match = line.match(/Got (\d+) profiles/);
              if (match) {
                sendEvent("progress", { step: "found", message: `Found ${match[1]} profiles` });
              }
            } else if (line.includes("STEP 2:")) {
              sendEvent("progress", { step: "enrich", message: "Enriching leads via Clay..." });
            } else if (line.includes("STEP 3:")) {
              sendEvent("progress", { step: "score", message: "Scoring leads..." });
            } else if (line.includes("STEP 4:")) {
              sendEvent("progress", { step: "export", message: "Exporting results..." });
            } else if (line.includes("PIPELINE COMPLETE")) {
              const leadsMatch = line.match(/Leads processed: (\d+)/);
              // Completion is handled after process exits
            }
          }
        });

        // Wait for process to complete
        const exitCode = await new Promise<number>((resolve) => {
          pythonProcess.on("close", (code) => resolve(code ?? 0));
        });

        if (exitCode !== 0) {
          sendEvent("error", { message: "Pipeline failed" });
          controller.close();
          return;
        }

        // Read final results
        try {
          const data = await fs.readFile(outputPath, "utf-8");
          const jsonData = JSON.parse(data);
          const leads = jsonData.leads || [];
          
          sendEvent("complete", { 
            message: `Found ${leads.length} leads!`,
            leads: leads
          });
        } catch (readErr) {
          sendEvent("error", { message: "Failed to read results" });
        }

        controller.close();

      } catch (err: any) {
        sendEvent("error", { message: err.message || "Unknown error" });
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  });
}
