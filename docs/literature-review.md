# Literature Review: AI-Assisted Terminal Orchestration with Local LLMs

## 1. Introduction

This review surveys the research underpinning invoq, a Linux-native CLI tool that uses locally-running large language models (LLMs) and the Model Context Protocol (MCP) to translate natural language into shell commands, debug failures, and execute system operations safely. The literature spans four interconnected themes: natural language to shell command translation, LLM-powered agentic tool use, local and edge LLM deployment for privacy and efficiency, and security in LLM agent systems.

---

## 2. Natural Language to Shell Command Translation

The foundational task for invoq is converting user intent into executable Bash commands. [Lin et al. (2018)](https://arxiv.org/pdf/1802.08979) introduced NL2Bash, a corpus of approximately 10,000 English-to-Bash pairs scraped from Stack Overflow and similar sources, establishing the benchmark problem of semantic parsing for shell interaction. Their goal was to let any user perform file manipulation, search, and scripting by stating intent in plain English, which maps directly to invoq's `ask` command. The dataset exposed the core difficulty: Bash commands are compositional, context-sensitive, and often involve chained utilities connected by pipes.

[Fu et al. (2023)](https://arxiv.org/pdf/2302.07845) updated this line of work with NL2CMD, an automatically generated dataset over six times larger than NL2Bash, produced by scraping Bash manual pages and training a back-translation model. Their evaluation of ChatGPT on this task demonstrated that general-purpose LLMs, without fine-tuning, had become competitive with dedicated semantic parsers, justifying invoq's decision to rely on instruction-tuned code models rather than purpose-built translators.

Evaluation methodology for this task has also matured. [Ghosh et al. (2024)](https://arxiv.org/pdf/2405.06807) argued that string-similarity metrics are insufficient for assessing shell command correctness and proposed an execution-based evaluation platform using containerised environments. Their work benchmarked seven LLMs on single-line and multi-line Bash generation, finding that models which produce syntactically similar but semantically different commands score well on string metrics yet fail in practice. This motivates invoq's design choice to always show the generated command to the user before execution, allowing human verification rather than trusting automated correctness alone.

[Westenfelder (2025)](https://arxiv.org/pdf/2502.06858) further reinforced the need for human-in-the-loop confirmation, noting that current state-of-the-art NL-to-shell models are used in practice with a workflow where users accept, reject, or edit model output. This is the exact confirmation pattern invoq implements at the MCP tool layer.

---

## 3. LLM-Powered Agentic Tool Use

invoq relies on a model that does not merely generate text but actively calls tools to execute commands, read files, and inspect the environment. The theoretical and empirical basis for this pattern comes from [Yao et al. (2023)](https://arxiv.org/pdf/2210.03629), who introduced ReAct, a framework in which LLMs interleave verbal reasoning traces with tool-calling actions. ReAct demonstrated that combining chain-of-thought reasoning with environment interaction outperforms either alone on tasks requiring multi-step information retrieval and decision-making. invoq's debug feature, which uses the model to investigate a failed command by reading logs, listing directories, and then proposing a fix, is a direct instance of the ReAct paradigm.

[Roziere et al. (2023)](https://arxiv.org/pdf/2308.12950) presented Code Llama, a family of open-weight code-specialised models derived from Llama 2, demonstrating that models fine-tuned on code data can interpret natural language instructions and translate them into shell commands and program synthesis tasks. Code Llama's Instruct variants were shown to handle command-line queries directly, establishing the viability of open-weight instruction-tuned models for the shell interaction invoq targets.

The architectural question of how to build terminal-native agentic tools is addressed directly by [Mehrotra et al. (2025)](https://arxiv.org/pdf/2603.05344v3), who surveyed open questions in designing terminal AI agents. They highlight that the design space for terminal-native tools is largely underexplored, that most production systems are closed-source, and that open-source frameworks either target benchmarks rather than interactive use or lack published technical reports. Their defence-in-depth safety architecture, with five independent safety layers, is conceptually aligned with invoq's separation of concerns across MCP tool schemas, command validation, and user confirmation.

---

## 4. Local and Edge LLM Deployment

A core requirement of invoq is that it runs entirely on the user's machine, with no data transmitted to external servers. This positions the project within the growing literature on local and edge LLM inference.

[Lin et al. (2024)](https://arxiv.org/pdf/2508.11269) introduced ELIB, a benchmarking tool for evaluating LLM inference on edge platforms including PC, mobile, and IoT devices. Their work confirmed that llama.cpp, a pure C++ inference framework, is among the most suitable choices for resource-constrained deployments due to its low overhead and efficient memory management. invoq uses Ollama, which wraps llama.cpp and exposes a local REST API, directly reflecting this recommendation for lightweight, easy-to-deploy inference runtimes.

[Shi et al. (2024)](https://arxiv.org/pdf/2407.18921) surveyed mobile edge intelligence for LLMs, noting that on-device inference eliminates privacy leakage and internet dependency at the cost of significant memory and compute constraints. Their taxonomy of compression techniques, including quantisation, pruning, and knowledge distillation, underpins invoq's model selection strategy: the project recommends quantised Qwen2.5-Coder models (1.5B for 4-6 GB RAM, 7B Q4 for 6-8 GB RAM) rather than full-precision alternatives, applying quantisation to fit within the RAM budgets of older consumer hardware.

[Xu et al. (2025)](https://arxiv.org/pdf/2504.00002) conducted a measurement study of LLM applications on mobile and edge devices, finding that only models under 4 billion parameters run acceptably on constrained hardware and that model compression can introduce significant performance degradation. Their findings confirm the upper-bound choices in invoq's model tier table and explain why models below 1.5B are not recommended even for the most constrained machines.

---

## 5. Security and Safety in LLM Agent Systems

Because invoq grants an LLM the ability to execute shell commands, security is the most critical design concern. The literature on this topic has grown rapidly and provides both threat models and mitigation strategies.

[Doshi et al. (2025)](https://arxiv.org/pdf/2601.08012) identified a fundamental limitation of model-based safeguards: risks in AI agents stem less from individual tool calls than from the composition of tools, data flows, and contexts, and probabilistic guardrails provide no formal guarantees. They propose combining safety engineering techniques with information flow control to derive verifiable constraints. This directly motivates invoq's allowlist-based architecture, where the MCP server refuses to execute any command not in the explicitly permitted set, providing a hard structural constraint rather than relying on model judgement.

[Luo et al. (2025)](https://arxiv.org/pdf/2601.10156) proposed ToolSafe, a step-level guardrail framework for LLM agents that monitors tool invocations dynamically. Their analysis showed that static rule-based guards have limited coverage, and that proactive step-level intervention is necessary for catching unsafe tool use as it emerges during multi-turn agent execution. This supports invoq's design of running validation before every tool call rather than only at the point of user input.

[Malara et al. (2025)](https://arxiv.org/pdf/2510.21236) introduced AgentBound, a framework that enforces operating-system-level access control policies on MCP servers. Their core argument is that relying on LLM guardrails alone is insufficient because aligned models can be jailbroken through prompt injection, and that enforceable OS-level policies are necessary for security guarantees. invoq's blocked pattern list, which prevents the LLM from ever calling commands such as `rm -rf` or `dd` regardless of the prompt, is a practical instantiation of this principle.

[Manhas et al. (2025)](https://arxiv.org/pdf/2507.06323) compared security postures of Function Calling and MCP architectures across seven LLM models, finding that MCP exhibits stronger containment properties due to its standardised client-server separation. However, they also identified that MCP's context-rich communication protocol creates higher susceptibility to cross-boundary attacks when isolation is not enforced. This finding supports invoq's decision to maintain a single, trusted local MCP server rather than allowing third-party MCP server connections.

[Hassan et al. (2025)](https://arxiv.org/pdf/2601.17549) conducted a security analysis of the MCP specification itself, finding that MCP's architecture amplifies attack success rates by 23-41% relative to direct function calls due to a lack of isolation boundaries between servers. Their work reinforces invoq's design choice to run the MCP server in-process and restrict the tool surface to a fixed, reviewed set of operations rather than supporting a pluggable server marketplace.

---

## 6. Summary

The research surveyed here validates the core design decisions behind invoq. NL-to-Bash translation has matured to the point where instruction-tuned open-weight models are competitive with dedicated semantic parsers, but human-in-the-loop confirmation remains necessary given persistent correctness failures. The ReAct framework provides theoretical grounding for the agentic investigate-then-fix pattern used in the debug feature. Edge LLM deployment literature confirms that quantised models in the 1.5B-7B range are viable on consumer hardware with 4-8 GB of RAM when using efficient runtimes such as llama.cpp. Security research consistently shows that structural, allowlist-based enforcement at the tool layer provides stronger guarantees than model-level guardrails alone, supporting invoq's tiered command validation and mandatory confirmation architecture.

---

## References

1. Lin, X. V., Wang, C., Zettlemoyer, L., and Ernst, M. D. (2018). NL2Bash: A Corpus and Semantic Parser for Natural Language Interface to the Linux Operating System. LREC 2018. [https://arxiv.org/pdf/1802.08979](https://arxiv.org/pdf/1802.08979)

2. Fu, Q., Teng, Z., Georgaklis, M., White, J., and Schmidt, D. C. (2023). NL2CMD: An Updated Workflow for Natural Language to Bash Commands Translation. arXiv:2302.07845. [https://arxiv.org/pdf/2302.07845](https://arxiv.org/pdf/2302.07845)

3. Ghosh, S., et al. (2024). Execution-Based Evaluation of Natural Language to Bash and PowerShell for Incident Remediation. arXiv:2405.06807. [https://arxiv.org/pdf/2405.06807](https://arxiv.org/pdf/2405.06807)

4. Westenfelder, F. (2025). LLM-Supported Natural Language to Bash Translation. arXiv:2502.06858. [https://arxiv.org/pdf/2502.06858](https://arxiv.org/pdf/2502.06858)

5. Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., and Cao, Y. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR 2023. arXiv:2210.03629. [https://arxiv.org/pdf/2210.03629](https://arxiv.org/pdf/2210.03629)

6. Roziere, B., et al. (2023). Code Llama: Open Foundation Models for Code. arXiv:2308.12950. [https://arxiv.org/pdf/2308.12950](https://arxiv.org/pdf/2308.12950)

7. Mehrotra, A., et al. (2025). Building Effective AI Coding Agents for the Terminal. arXiv:2603.05344. [https://arxiv.org/pdf/2603.05344v3](https://arxiv.org/pdf/2603.05344v3)

8. Lin, R., et al. (2024). Inference Performance Evaluation for LLMs on Edge Devices. arXiv:2508.11269. [https://arxiv.org/pdf/2508.11269](https://arxiv.org/pdf/2508.11269)

9. Shi, Y., et al. (2024). Mobile Edge Intelligence for Large Language Models: A Contemporary Survey. arXiv:2407.18921. [https://arxiv.org/pdf/2407.18921](https://arxiv.org/pdf/2407.18921)

10. Xu, J., et al. (2025). Are We There Yet? A Measurement Study of Efficiency for LLM Applications on Mobile Devices. arXiv:2504.00002. [https://arxiv.org/pdf/2504.00002](https://arxiv.org/pdf/2504.00002)

11. Doshi, A., et al. (2025). Towards Verifiably Safe Tool Use for LLM Agents. arXiv:2601.08012. [https://arxiv.org/pdf/2601.08012](https://arxiv.org/pdf/2601.08012)

12. Luo, Y., et al. (2025). ToolSafe: Enhancing Tool Invocation Safety of LLM-based Agents. arXiv:2601.10156. [https://arxiv.org/pdf/2601.10156](https://arxiv.org/pdf/2601.10156)

13. Malara, M., et al. (2025). Securing AI Agent Execution (AgentBound). arXiv:2510.21236. [https://arxiv.org/pdf/2510.21236](https://arxiv.org/pdf/2510.21236)

14. Manhas, A., et al. (2025). A Comparative Vulnerability Assessment of LLM Agent Architectures. arXiv:2507.06323. [https://arxiv.org/pdf/2507.06323](https://arxiv.org/pdf/2507.06323)

15. Hassan, O., et al. (2025). Breaking the Protocol: Security Analysis of the Model Context Protocol Specification. arXiv:2601.17549. [https://arxiv.org/pdf/2601.17549](https://arxiv.org/pdf/2601.17549)
