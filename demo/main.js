const express = require('express');
const app = express()

app.post('/ocr', (req, res) => {
    // Trả tiền theo số lượt sử dụngdụng, mỗi lượt dùng trả $1
    const text = await runOCR(req.body.image)
    res.status(200).send({
        raw: text,
    })
})

app.post('/structured-ocr', (req, res) => {
    // Trả tiền theo số lượng sử dụng, số tiền cần trả được quyết định bởi
    // lượng token đã dùng
    // Đặt cọc trước một số tiền
    idempotencyKey = crypto.randomUUID()
    await fetch("http://localhost:9000/billing", {
        method: "POST",
        headers: {
            "idempotency-key": idempotencyKey,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            api_key_uuid: req.header("X-API-Key-UUID"),
            service_name: "structured-ocr",
            amount: { value: 1 + 10, scale: 1 }, // $1 OCR + $10 LLM
        })
    })

    const text = await runOCR(req.body.image)
    const llmOutput = await fetch(
        "http://localhost:9000/ai-gateway/ag-ui/gpt-oss-20b", {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            thread_id: crypto.randomUUID(),
            run_id: crypto.randomUUID(),
            state: null,
            messages: [{
                role: "user", content: `
                Transform the following text into this schema: ${req.body.schema}

                Text: ${text}`
            }],
            tools: [],
            context: [],
            forwarded_props: null
        })
    })
    const { usedTokens, structured_json } = processLLMOutput(llmOutput)
    res.status(200).send({
        raw: text,
        structured: structured_json,
    })

    // Chốt số tiền đã sử dụng
    fetch(`http://localhost:9000/billing/${idempotencyKey}/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ real_amount: calculatePrice(usedTokens) })
    })
})

const port = 3000
app.listen(port, () => {
    console.log(`App listening on port ${port}`)
})