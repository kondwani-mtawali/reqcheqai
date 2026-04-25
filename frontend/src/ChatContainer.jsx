{/* 
Author(s) : Kondwani & Grant
Change Log:
Date Created: 04/12/2026
Last Edited: 4/25/2026
*/}

import { useState } from "react";
import styles from './ChatContainer.module.css'

export default function ChatContainer() {
    const [inputValue, setInputValue] = useState("")
    // Report
    // DON'T TOUCH:
    // Don't know why it crashes when you remove response or report.
    // Will need to be looked at, but don't touch.
    const [response, setResponse] = useState("")
    const [report, setReport] = useState("")
    const [score, setScore] = useState("")
    const [isLoading, setIsLoading] = useState(false)

    async function submitHandle() {
        // For DevTools + Manual Testing, shows the button is actually registering a button click when pressed.
        console.log("Button clicked")
        if (!inputValue.trim()) return
        setIsLoading(true)
        setResponse("")
        setReport("")
        setScore("")


        try {

            // NOTE: Make sure url ending tag is correct.
            // FastAPI is expecting the exact path.
            // apiUrl gets the api url from an env variable and if there is not one defined
            // it will default to "http://localhost:8000".
            // Would help when a developers local environent uses port 5173 instead of 8000.
            // Rather than hardcoding and it crashing for one developer, this allows it to work for both.
            const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
            const res = await fetch(`${apiUrl}/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ requirement: inputValue }),
            })

            const data = await res.json()
            // Logging the data to ensure that there is data in the fields.
            console.log(data)
            setResponse(data.response)
            setReport(data.report)
            setScore(data.req_score)

        } catch (error) {

            // Log the error for testing/debugging purposes.
            console.log("Chat request failed:", error)
            setResponse("Something went wrong.")
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className={styles.page}>
            <div className={styles.inputContainer}>
                <textarea
                    className={styles.inputContainer}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Enter your requirements here..."
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button onClick={submitHandle} disabled={isLoading}>
                        {/* When reading disply: Analzing... + Button Name = Analyze*/}
                        {isLoading ? "Analyzing..." : "Analyze"}
                    </button>
                </div>
                {/* Display the response if there is one. */}
                {/*  If there is no input = no response. */}
                {report && (
                    <div>
                        <p>Functional: {report.functional_portion}</p>
                        <p>Non Functional: {report.non_functional_portion}</p>
                        <p>Ambiguity Level: {report.ambiguity_level}</p>
                        <p>Active Voice: {report.active_voice}</p>
                        <p>Score: {score}</p>
                    </div>
                )}

            </div>
        </div>
    )
}