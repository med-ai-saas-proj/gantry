import express from "express";
import { HttpAgent } from "@ag-ui/client";

const app = express();
app.use(express.json());
app.use((req, res, next) => {
  console.log(`${req.method} request received at ${req.url}`);
  next(); // Always call next to move to the next handler!
});

async function runOCR(image) {
  return `PATIENT PROFILE
  Patient Name	Le Van Binh
  Patient #	P-003
  Date of Birth	10/12/1990
  Gender	Male
  Medical Record No.	MRN-2024-003215
  Phone	(555) 123-4567
  Email	tranvana@example.com
  Address	12 Le Loi Street, District 1, Ho Chi Minh City`;
}

function calculatePrice(json) {
  return { value: Math.round(json.length / 100), scale: 1 }
}

app.post("/ocr", async (req, res) => {
  // Trả tiền theo số lượt sử dụngdụng, mỗi lượt dùng trả $1
  const text = await runOCR(req.body.image);
  res.status(200).send({ raw: text });
});

app.post("/structured-ocr", async (req, res) => {
  // Trả tiền theo số lượng sử dụng, số tiền cần trả được quyết định bởi
  // lượng token đã dùng
  // Đặt cọc trước một số tiền
  const hold_response = await fetch("http://localhost:9000/billing", {
    method: "POST",
    headers: {
      "idempotency-key": crypto.randomUUID(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      api_key_uuid: req.header("X-API-Key-UUID"),
      service_name: "structured-ocr",
      amount: { value: 1 + 10, scale: 1 }, // $1 OCR + $10 LLM
    }),
  });
  const hold_id = await hold_response.text();

  const text = await runOCR(req.body.image);
  const llm = new HttpAgent({
    url: "http://localhost:9000/ai-gateway/ag-ui/gpt-oss-20b",
  });
  llm.setMessages([{
    id: crypto.randomUUID(),
    role: "user",
    content: `Transform the following text into structured output. Use the output tool to response.
    Text: ${text}`,
  }])
  let json = "{}"
  await llm.runAgent({
    context: [],
    runId: crypto.randomUUID(),
    tools: [{
      name: "output",
      description: "Call this to response.",
      parameters: {
        type: "object",
        properties: {
          patientName: {
            type: "string",
            description: "The full name of the patient.",
          },
          patientId: {
            type: "string",
            description: "Unique patient ID/number (e.g., P-003).",
          },
          dateOfBirth: {
            type: "string",
            description:
              "Date of birth of the patient (formatted as MM/DD/YYYY or YYYY-MM-DD).",
          },
          gender: {
            type: "string",
            enum: ["Male", "Female", "Other", "Unknown"],
            description: "The gender of the patient.",
          },
          medicalRecordNumber: {
            type: "string",
            description: "Medical Record Number (MRN).",
          },
          phone: {
            type: "string",
            description: "Primary contact phone number for the patient.",
          },
          email: {
            type: "string",
            description: "Email address of the patient.",
          },
          address: {
            type: "string",
            description: "Full physical or mailing address of the patient.",
          },
        },
        required: [
          "patientName",
          "patientId",
          "dateOfBirth",
          "gender",
          "medicalRecordNumber",
          "phone",
          "email",
          "address",
        ],
        additionalProperties: false,
      },
    }],
  }, {
    "onNewToolCall": (toolCall) => {
      json = toolCall.toolCall.function.arguments
      llm.abortRun()
    }
  });
  res.status(200).send({ raw: text, structured: JSON.parse(json) });

  // Chốt số tiền đã sử dụng
  await fetch(`http://localhost:9000/billing/${hold_id}/capture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ real_amount: calculatePrice(json) }),
  });
});

app.get("/health", async (req, res) => {
  res.status(200).send({"hello": "world"})
})

const port = 6969;
const server = app.listen(port, () => console.log(`App listening on port ${port}`));
server.on("error", (err) => { console.error(err); process.exit(1); });
