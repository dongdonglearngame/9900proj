import type { ChoiceLetter, ChoiceMap, PredictResponse } from "../types/api";

interface PredictionViewProps {
  choices: ChoiceMap;
  groundTruth: ChoiceLetter | null;
  prediction: PredictResponse | null;
}

export function PredictionView({ choices, groundTruth, prediction }: PredictionViewProps) {
  const predictedAnswer = prediction?.answer;
  const isCorrect = Boolean(predictedAnswer && groundTruth && predictedAnswer === groundTruth);

  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Step 3 - Model Output</h2>
        <p>Prediction from {prediction?.model ?? "the selected model"} vs. ground truth.</p>
      </div>

      <div className="answer-grid">
        <article>
          <span className="readout-label">Model Predicted</span>
          <div className="answer-card">
            <span className="choice-badge">{predictedAnswer ?? "-"}</span>
            <p>{predictedAnswer ? choices[predictedAnswer] : "Run the model to see its answer."}</p>
          </div>
        </article>

        <article>
          <span className="readout-label">Ground Truth</span>
          <div className="answer-card success-card">
            <span className="choice-badge success-badge">{groundTruth ?? "-"}</span>
            <p>{groundTruth ? choices[groundTruth] : "Hidden until prediction completes."}</p>
          </div>
        </article>
      </div>

      <div className="status-row">
        <span>Prediction status</span>
        <strong className={`status-pill ${isCorrect ? "success" : "danger"}`}>
          {isCorrect ? "Correct" : "Incorrect - explanation needed"}
        </strong>
      </div>
    </section>
  );
}
