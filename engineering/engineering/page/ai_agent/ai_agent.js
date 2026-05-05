frappe.pages["ai-agent"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "AI Agent",
		single_column: true,
	});

	$(page.body).html(`
		<style>
			.ai-agent-page {
				min-height: calc(100vh - 120px);
				padding: 30px 20px 60px;
				background:
					radial-gradient(circle at top left, rgba(0, 140, 255, 0.18), transparent 35%),
					radial-gradient(circle at top right, rgba(140, 0, 255, 0.18), transparent 35%),
					radial-gradient(circle at bottom center, rgba(0, 255, 180, 0.10), transparent 30%),
					linear-gradient(135deg, #0a0f1f 0%, #111827 45%, #0b1220 100%);
				color: #e5eefc;
			}

			.ai-agent-shell {
				max-width: 1100px;
				margin: 0 auto;
			}

			.ai-agent-hero {
				position: relative;
				overflow: hidden;
				border: 1px solid rgba(255, 255, 255, 0.12);
				border-radius: 24px;
				padding: 28px;
				margin-bottom: 24px;
				background: rgba(255, 255, 255, 0.06);
				backdrop-filter: blur(14px);
				box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
			}

			.ai-agent-hero::before {
				content: "";
				position: absolute;
				width: 260px;
				height: 260px;
				top: -120px;
				right: -80px;
				background: radial-gradient(circle, rgba(0, 183, 255, 0.35), transparent 65%);
				pointer-events: none;
			}

			.ai-agent-badge {
				display: inline-flex;
				align-items: center;
				gap: 8px;
				padding: 6px 12px;
				border-radius: 999px;
				background: rgba(0, 255, 191, 0.10);
				border: 1px solid rgba(0, 255, 191, 0.25);
				color: #9fffe0;
				font-size: 12px;
				font-weight: 600;
				letter-spacing: 0.4px;
				margin-bottom: 14px;
			}

			.ai-agent-dot {
				width: 8px;
				height: 8px;
				border-radius: 50%;
				background: #00ffbf;
				box-shadow: 0 0 12px #00ffbf;
			}

			.ai-agent-title {
				font-size: 34px;
				font-weight: 700;
				line-height: 1.1;
				margin-bottom: 10px;
				color: #ffffff;
			}

			.ai-agent-subtitle {
				font-size: 15px;
				line-height: 1.7;
				color: #c7d7f2;
				max-width: 780px;
				margin-bottom: 0;
			}

			.ai-agent-grid {
				display: grid;
				grid-template-columns: 1.6fr 0.8fr;
				gap: 24px;
			}

			.ai-agent-card,
			.ai-agent-side-card {
				border: 1px solid rgba(255, 255, 255, 0.10);
				border-radius: 22px;
				background: rgba(255, 255, 255, 0.05);
				backdrop-filter: blur(12px);
				box-shadow: 0 16px 40px rgba(0, 0, 0, 0.28);
			}

			.ai-agent-card {
				padding: 24px;
			}

			.ai-agent-card-header {
				display: flex;
				justify-content: space-between;
				align-items: center;
				margin-bottom: 18px;
			}

			.ai-agent-card-title {
				font-size: 18px;
				font-weight: 700;
				color: #ffffff;
				margin: 0;
			}

			.ai-agent-card-subtitle {
				font-size: 13px;
				color: #9fb4d9;
				margin: 0;
			}

			.ai-agent-question {
				width: 100%;
				min-height: 150px;
				resize: vertical;
				border-radius: 18px;
				border: 1px solid rgba(0, 183, 255, 0.24);
				background: rgba(7, 14, 30, 0.80);
				color: #f3f8ff;
				padding: 18px;
				font-size: 15px;
				line-height: 1.6;
				outline: none;
				box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.02);
			}

			.ai-agent-question::placeholder {
				color: #7e95bc;
			}

			.ai-agent-question:focus {
				border-color: rgba(0, 183, 255, 0.65);
				box-shadow: 0 0 0 3px rgba(0, 183, 255, 0.12);
			}

			.ai-agent-actions {
				display: flex;
				align-items: center;
				gap: 12px;
				margin-top: 16px;
				flex-wrap: wrap;
			}

			.ai-agent-ask-btn {
				border: none;
				border-radius: 14px;
				padding: 12px 20px;
				font-weight: 700;
				font-size: 14px;
				color: #06111f;
				background: linear-gradient(135deg, #00d4ff 0%, #00ffbf 100%);
				box-shadow: 0 10px 24px rgba(0, 212, 255, 0.28);
				transition: transform 0.18s ease, box-shadow 0.18s ease;
			}

			.ai-agent-ask-btn:hover {
				transform: translateY(-1px);
				box-shadow: 0 14px 30px rgba(0, 212, 255, 0.35);
			}

			.ai-agent-clear-btn {
				border: 1px solid rgba(255, 255, 255, 0.12);
				border-radius: 14px;
				padding: 12px 18px;
				font-weight: 600;
				font-size: 14px;
				color: #d8e4fa;
				background: rgba(255, 255, 255, 0.04);
			}

			.ai-agent-hint {
				font-size: 12px;
				color: #89a0c8;
			}

			.ai-agent-answer-wrap {
				margin-top: 24px;
			}

			.ai-agent-answer-label {
				font-size: 12px;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: 0.8px;
				color: #7ee7ff;
				margin-bottom: 10px;
			}

			.ai-agent-answer {
				min-height: 180px;
				border-radius: 18px;
				padding: 18px;
				background:
					linear-gradient(180deg, rgba(13, 22, 43, 0.95), rgba(9, 16, 31, 0.95));
				border: 1px solid rgba(0, 183, 255, 0.16);
				color: #ebf3ff;
				font-size: 15px;
				line-height: 1.7;
				white-space: pre-wrap;
			}

			.ai-agent-answer.is-thinking {
				color: #9ee9ff;
			}

			.ai-agent-side-card {
				padding: 22px;
				height: fit-content;
			}

			.ai-agent-side-title {
				font-size: 16px;
				font-weight: 700;
				color: #ffffff;
				margin-bottom: 14px;
			}

			.ai-agent-side-list {
				display: flex;
				flex-direction: column;
				gap: 10px;
			}

			.ai-agent-chip {
				padding: 12px 14px;
				border-radius: 14px;
				background: rgba(255, 255, 255, 0.04);
				border: 1px solid rgba(255, 255, 255, 0.08);
				color: #d8e4fa;
				font-size: 13px;
				line-height: 1.5;
			}

			.ai-agent-side-note {
				margin-top: 18px;
				padding: 14px;
				border-radius: 14px;
				background: rgba(0, 255, 191, 0.08);
				border: 1px solid rgba(0, 255, 191, 0.14);
				color: #bafbe7;
				font-size: 13px;
				line-height: 1.6;
			}

			@media (max-width: 900px) {
				.ai-agent-grid {
					grid-template-columns: 1fr;
				}

				.ai-agent-title {
					font-size: 28px;
				}
			}
		</style>

		<div class="ai-agent-page">
			<div class="ai-agent-shell">

				<div class="ai-agent-hero">
					<div class="ai-agent-badge">
						<span class="ai-agent-dot"></span>
						<span>INTELLIGENT ERP ASSISTANT</span>
					</div>

					<div class="ai-agent-title">AI Agent</div>

					<p class="ai-agent-subtitle">
						Ask questions about your ERP data, analyse operational insights, and interact with your future AI workflows from one modern control center.
					</p>
				</div>

				<div class="ai-agent-grid">
					<div class="ai-agent-card">
						<div class="ai-agent-card-header">
							<div>
								<p class="ai-agent-card-title">Ask AI Agent</p>
								<p class="ai-agent-card-subtitle">Start with oil samples, maintenance, and operational analysis.</p>
							</div>
						</div>

						<textarea
							class="ai-agent-question"
							placeholder="Example: Check oil samples for abnormal readings and summarise high-risk equipment."
						></textarea>

						<div class="ai-agent-actions">
							<button class="ai-agent-ask-btn">Ask AI</button>
							<button class="ai-agent-clear-btn">Clear</button>
							<div class="ai-agent-hint">Tip: Press Ctrl + Enter to submit</div>
						</div>

						<div class="ai-agent-answer-wrap">
							<div class="ai-agent-answer-label">Response</div>
							<div class="ai-agent-answer">Your AI response will appear here.</div>
						</div>
					</div>

					<div class="ai-agent-side-card">
						<div class="ai-agent-side-title">Suggested Questions</div>

						<div class="ai-agent-side-list">
							<div class="ai-agent-chip">Which oil samples show abnormal wear metals?</div>
							<div class="ai-agent-chip">Which equipment has repeat contamination issues?</div>
							<div class="ai-agent-chip">Summarise urgent maintenance risks this month.</div>
							<div class="ai-agent-chip">Compare latest oil samples with previous readings.</div>
							<div class="ai-agent-chip">Which units need immediate follow-up?</div>
						</div>

						<div class="ai-agent-side-note">
							Future ready: this page can later support multiple ERP tools, role-based answers, and audit logging.
						</div>
					</div>
				</div>

			</div>
		</div>
	`);

	const $body = $(page.body);
	const $question = $body.find(".ai-agent-question");
	const $answer = $body.find(".ai-agent-answer");

	function ask_ai() {
		const question = $question.val();

		if (!question) {
			frappe.msgprint("Please enter a question.");
			return;
		}

		$answer.addClass("is-thinking").html("Thinking...");

		frappe.call({
			method: "engineering.controllers.ai_agent.ask_ai_agent",
			args: { question },
			callback: function (r) {
				$answer.removeClass("is-thinking").html(
					r.message?.answer || r.message?.message || "No response."
				);
			},
			error: function () {
				$answer.removeClass("is-thinking").html("Something went wrong.");
			},
		});
	}

	$body.find(".ai-agent-ask-btn").on("click", function () {
		ask_ai();
	});

	$body.find(".ai-agent-clear-btn").on("click", function () {
		$question.val("");
		$answer.removeClass("is-thinking").html("Your AI response will appear here.");
	});

	$question.on("keydown", function (e) {
		if (e.ctrlKey && e.key === "Enter") {
			ask_ai();
		}
	});

	$body.find(".ai-agent-chip").on("click", function () {
		$question.val($(this).text());
		$question.focus();
	});
};