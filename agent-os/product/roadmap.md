# Product Roadmap

## 1. Project Foundation
**Status:** In Progress

- [x] 1.1 Set up project structure matching existing projects (svcs-di, tdom-svcs)
- [ ] 1.2 Create comprehensive examples
- [ ] 1.3 Add documentation with deep research on python-sdk and Pydantic AI
- [ ] 1.4 Configure pytest setup proving python-sdk works correctly

## 2. Test-Driven Refactoring
**Status:** Not Started

- [ ] 2.1 Copy existing python-sdk into this project
- [ ] 2.2 Verify python-sdk integration works
- [ ] 2.3 Refactor tests to be more granular and pluggable
- [ ] 2.4 Add mocking for model calls

## 3. Pydantic AI Migration
**Status:** Not Started

- [ ] 3.1 Introduce HTTP server into asyncio loop
- [ ] 3.2 Perform minimal transition to Pydantic AI project structure
- [ ] 3.3 Gradually port python-sdk "tools" into Pydantic AI tools
- [ ] 3.4 Convert to best-practices Pydantic AI project

## 4. ACP Integration
**Status:** Not Started

- [ ] 4.1 Implement dynamic tool discovery via ACP
- [ ] 4.2 Register IDE tools automatically
- [ ] 4.3 Enable agent awareness of PyCharm capabilities

## 5. Web UI Development
**Status:** Not Started

- [ ] 5.1 Design multi-agent tracking interface
- [ ] 5.2 Build browser-based monitoring dashboard
- [ ] 5.3 Implement agent interaction controls
- [ ] 5.4 Add simultaneous agent management features

## 6. Advanced Features
**Status:** Not Started

- [ ] 6.1 Create domain-specific skills and policies framework
- [ ] 6.2 Implement custom deterministic policies for project-specific rules
- [ ] 6.3 Add support for free-threaded Python (PEP 703)
- [ ] 6.4 Optimize for parallel agent operations across multiple cores

## Research

### Monty For Code Mode

**References:**
- [Pydantic Monty announcement](https://news.ycombinator.com/item?id=46920388)
- [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
- [Anthropic Programmatic Tool Calling](https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling)

Pydantic introduced Monty as a radical improvement to agent tool execution performance. Similar work from Cloudflare and Anthropic shows this is a key area for optimization. Code mode allows agents to generate and execute tool calls programmatically rather than through traditional JSON-based tool use, resulting in:

- Faster tool invocation
- More efficient token usage
- Better agent reasoning about tool composition
- Reduced latency in multi-step workflows

**Relevance to Punie:** As Punie delegates tool execution to PyCharm via ACP, implementing code mode patterns could significantly improve performance, especially for complex multi-tool workflows. This could be particularly beneficial for the advanced features in Phase 6, where parallel agent operations and free-threaded execution would benefit from optimized tool calling patterns.
