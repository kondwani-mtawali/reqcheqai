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
    const [atomicScore, setAtomicScore] = useState("")
    const [measureScore, setMeasureScore] = useState("")
    const [complexScore, setComplexScore] = useState("")
    const [readScore, setReadScore] = useState("")
    const [reqScore, setReqScore] = useState("")
    const [isLoading, setIsLoading] = useState(false)

    // NEW: Feedback Endpoint State Variables
    const [reqcheq_id, setreqcheq_id] = useState(null)
    const [feedback, setFeedback] = useState(null)
    const [isLoadingFeedback, setIsLoadingFeedback] = useState(false)

    async function submitHandle() {
        // For DevTools + Manual Testing, shows the button is actually registering a button click when pressed.
        console.log("Button clicked")
        if (!inputValue.trim()) return
        setIsLoading(true)
        setResponse("")
        setReport("")
        setAtomicScore("")
        setMeasureScore("")
        setMeasureScore("")
        setComplexScore("")
        setReadScore("")
        setReqScore("")
        // NEW: Feedback Endpoint States
        setreqcheq_id(null)
        setFeedback(null)

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
            setAtomicScore(data.atomicity_score)
            setMeasureScore(data.measurability_score)
            setComplexScore(data.complexity_score)
            setReadScore(data.readability_score)
            setReqScore(data.req_score)

            // NEW: Save the req_cheq id for feedback endpoint call
            setreqcheq_id(data.reqcheq_id)
            console.log("Saved ID:", data.reqcheq_id)


        } catch (error) {

            // Log the error for testing/debugging purposes.
            console.log("Chat request failed:", error)
            setResponse("Something went wrong.")
        } finally {
            setIsLoading(false)
        }
    }

    // NEW FUNCTION: Feedback Endpoint Function
    async function generateFeedback() {
        console.log("button clicked")
        
        // Verify that the ID exists
        if (!reqcheq_id) { 
            alert("No reqcheq_id found")
            return;
        }
        console.log("Saved reqcheq_id", reqcheq_id, "Type:", reqcheq_id.type)

       setIsLoadingFeedback(true)
    try {
            const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
            const res = await fetch(`${apiUrl}/feedback`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reqcheq_id: Number(reqcheq_id) }),
            })

            const feedbackData = await res.json()
            console.log(reqcheq_id)
            console.log("Feedback response:", feedbackData) // Observe LLM feedback
            if (res.status === 422) {
            console.error("Validation Errors:", feedbackData.detail);
        }
            setFeedback(feedbackData)
            
        } catch (error) {
            // Log the error for testing/debugging purposes.
            console.log("Feedback Response Failed:", error)
            setFeedback("Something went wrong.")
        } finally {
            setIsLoadingFeedback(false)
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
                        <h2>Categorical / Quantitative Analysis</h2>
                        <p>Type of Requirement: {report.type}</p>
                        <p>Functional: {report.functional_portion}</p>
                        <p>Non-Functional Portion: {report.non_functional_portion}</p>
                        <p>Class: {report.class}</p>
                        <p>Ambiguity Score: {report.ambiguity_score}</p>
                        <p>Active Voice: {report.active_voice}</p>
                        <p>Atomicity Score: {atomicScore}</p>
                        <p>Measurability Score: {measureScore}</p>
                        <p>Complexity Score: {complexScore}</p>
                        <p>Readability Score: {readScore}</p>
                        <p>Overall Requirement Score: {reqScore}</p>
                    </div>
                )}
                {/* NEW BUTTON: Generate Feedback */}
                    <button onClick={generateFeedback} disabled={isLoadingFeedback}>
                        {/* When reading disply: Generating... + Button Name = GetFeedback*/}
                        {isLoadingFeedback ? "Generating..." : "GetFeedback"}
                    </button>

                {/* NEW FEEDBACK INFORMATION*/}
                {feedback && (
                    <div>
                        <h2>Qualitative Feedback</h2>
                        <h3>Disclaimer:</h3>
                        <p>**{feedback.disclaimer}**</p>
                        <h3>Feedback:</h3>
                        <p>{feedback.feedback}</p>
                        <h3>Requirement Strengths:</h3>
                        <p>{feedback.requirement_strengths}</p>
                        <h3>Requirement Weaknesses:</h3>
                        <p>{feedback.requirement_weaknesses}</p>
                        <h3>Suggestions:</h3>
                        <p>{feedback.suggestions}</p>
                        <h4>Improved Version</h4>
                        <p>{feedback.improved_version}</p>
                    </div>


                )}



            </div>
        </div>
    )
}