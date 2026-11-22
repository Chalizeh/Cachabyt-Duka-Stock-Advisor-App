# Group of Three – Roles and Presentation Plan

All members should understand the complete application. The roles below divide the work but should not create three separate projects.

## Member 1 – Python and Inventory Lead
**Main responsibility:** Core stock-management functions.

Tasks:
- Explain the problem and introduce the project.
- Maintain `data/stock.json` and the product catalogue.
- Explain `show_stock`, `record_sale`, `add_stock` and `show_low_stock`.
- Test stock deductions, restocking and low-stock alerts.
- Make at least three meaningful commits, for example:
  1. `Create canteen product catalogue`
  2. `Add stock checking and low-stock warning`
  3. `Implement sale and restock functions`

## Member 2 – AI, API and Memory Lead
**Main responsibility:** Gemini integration and prompt design.

Tasks:
- Explain the two R-T-C-C-O prompts.
- Set up the Gemini API key securely in `.env`.
- Explain how `history` stores user and assistant messages.
- Demonstrate that the full history is sent on each turn.
- Explain JSON validation, one retry and the final summary call.
- Make at least three meaningful commits, for example:
  1. `Add system and summary prompts`
  2. `Connect Gemini and send conversation history`
  3. `Validate JSON responses and save session summary`

## Member 3 – Student Orders, Testing and Documentation Lead
**Main responsibility:** Student experience and project quality.

Tasks:
- Explain how a student checks availability and submits an advance-order request.
- Demonstrate the order list, awaiting-payment status, seller payment verification, unpaid-buyer reminder and collection status updates.
- Test invalid input, insufficient stock, missing session files and offline/local mode.
- Maintain README, report, sample session and presentation.
- Make at least three meaningful commits, for example:
  1. `Add student advance-order feature`
  2. `Test error handling and create sample session`
  3. `Write README and project report`

## Suggested 10-minute live demonstration

| Time | Presenter | Demonstration |
|---|---|---|
| 0:00–2:00 | Member 1 | Problem, canteen menu, stock display and low-stock warning |
| 2:00–5:00 | Member 2 | Four-turn AI conversation showing memory, JSON and summary |
| 5:00–6:00 | Member 3 | Student order request, pending status and a deliberate error test |
| 6:00–8:00 | All | Explain prompts, Python logic, local memory and API |
| 8:00–10:00 | All | Questions and answers |

## Example four-turn conversation

1. Owner: `How many samosas are available?`
2. Owner: `We sold 12 samosas. What is the remaining quantity?` (First record the sale through the owner menu.)
3. Owner: `Which products are running low?`
4. Owner: `Based on what we discussed, what should I restock first?`

The fourth answer should make use of the earlier conversation and the current stock snapshot.

## Individual submission

Each member submits individually to Google Classroom:
- Group report
- GitHub repository link showing their own commits
- Personal reflection of 5–8 sentences describing their contribution and learning
