# Real-World Data Collection Impact Assessment

**Date:** 2026-02-16
**Context:** Phase 27.5 Honest Audit revealed gaps in cross-tool workflows (0% success) and field access (60% success)

## Executive Summary

Real-world usage data collection would have **REALLY BIG** impact on cross-tool workflows (the #1 failure mode), **BIG** impact on field access patterns, and **MEDIUM** impact on LSP tool selection.

The key insight: Synthetic examples teach WHAT tools exist. Real-world data teaches WHEN to use them together, HOW to use their results, and WHY to choose one over another.

---

## Impact Assessment by Area

### 1. Cross-Tool Workflows (0% → 60%+ target)

**Impact: REALLY BIG 🔥**

**Current State:**
- Model calls ONE tool, never ALL tools in sequence
- Cross-tool validation: 0/5 (0%)
- Complete failure mode

**What Real-World Data Would Reveal:**

1. **Actual multi-step workflows users need:**
   - Not synthetic "run all quality checks"
   - Real sequences: "check if tests pass, if not lint the failing files"
   - Context-dependent chains: "git diff → read those files → ruff them"

2. **Natural language patterns:**
   - "check status AND diff" vs "check status then diff" vs "check status, if dirty then diff"
   - Implicit sequencing: "review the changes" might mean git_diff + read_file
   - Explicit steps: "first check types, then run tests"

3. **Dependency patterns:**
   - tool1 result → decision → tool2(using tool1 results)
   - Example: `git_diff()` → get file list → `read_file()` on each
   - Example: `ruff_check()` → if violations → `read_file()` to show context

4. **Common sequences people actually use:**
   - `git diff` → read those specific files (not all files)
   - `ruff_check` → fix issues → `pytest_run` to verify fix didn't break tests
   - `goto_definition` → read that file → `ruff_check` that specific file
   - `git_status` → if staged files → `git_diff` with staged=True

**Why Synthetic Fails:**
We invented workflows we THINK people want. Real data shows what they ACTUALLY want and how they phrase it naturally.

**Example Gap:**
- **Synthetic:** "Run full quality check: ruff, pytest, and typecheck"
- **Real user:** "lint this file, if there are errors run tests to see if I broke anything"
- **Difference:** Real user has conditional logic and context-awareness

**Data Collection Strategy:**
- Capture ANY request involving multiple operations
- Log the tool sequence executed and intermediate results
- Record natural language phrasing
- Track decision points (if/else based on tool results)

---

### 2. Field Access Patterns (60% → 80%+ target)

**Impact: BIG 🔥**

**Current State:**
- Model sometimes accesses result.errors, result.error_count
- Field access validation: 3/5 (60%)
- Inconsistent behavior

**What Real-World Data Would Reveal:**

1. **Which fields users ACTUALLY care about:**
   - Maybe `error_count` is more useful than iterating `errors`
   - Maybe users want `failed` but rarely access `passed`
   - Maybe `file_count` matters more than iterating all `files`
   - Maybe `success` boolean is checked most often

2. **Real conditional logic patterns:**
   ```python
   # Synthetic might do:
   for error in result.errors:
       print(error)

   # Real users might do:
   if result.error_count > 0:
       print(f"Found {result.error_count} errors")
       if result.error_count < 10:
           for error in result.errors:
               print(error)
       else:
           print("Too many to show!")
   ```

3. **Real iteration patterns:**
   - Limiting: `for err in result.errors[:10]:`
   - Filtering: `for err in result.errors if err.severity == 'error':`
   - Grouping: `by_file = groupby(result.errors, key=lambda e: e.file)`

4. **Field combinations that make sense:**
   - Accessing `error_count` AND `errors` together (check then iterate)
   - Using `file_count` to decide whether to iterate `files`
   - Checking `success` before accessing data fields

**Why Synthetic Fails:**
We guessed which fields matter and generated examples accessing all fields evenly. Real data shows actual usage patterns and field importance.

**Example Gap:**
- **Synthetic:** Accesses all fields equally, always iterates full lists
- **Real usage:** Heavy preference for count fields (quick checks), only iterates when count is reasonable, often limits iterations

**Data Collection Strategy:**
- Log which result fields are accessed in real code
- Track conditional logic using field values
- Capture iteration patterns (full iteration vs limited vs filtered)
- Record field access frequency distribution

---

### 3. New LSP Tools (80% → 90%+ target)

**Impact: MEDIUM 🟡**

**Current State:**
- hover, document_symbols, workspace_symbols mostly work
- New LSP validation: 4/5 (80%)
- Already decent performance

**What Real-World Data Would Reveal:**

1. **When users ACTUALLY want hover vs goto_definition:**
   - "What does UserService do?" → hover (documentation)
   - "Where is UserService defined?" → goto_definition (navigation)
   - "Show me UserService" → ambiguous, context helps

2. **Real symbol names and contexts:**
   - Real: `UserService`, `process_payment`, `validate_token`
   - Synthetic: `execute_code`, `Symbol`, `TypeChecker`
   - Real names might have patterns we haven't captured

3. **Real file paths and structure:**
   - Real: `src/auth/services/user.py`, `apps/api/views/payment.py`
   - Synthetic: `src/app.py`, `src/models/base.py`
   - Real structure reveals navigation patterns

4. **Context clues for tool selection:**
   - "what does X do?" → hover
   - "where is X?" → goto_definition
   - "find X" → workspace_symbols
   - "show me the structure of X" → document_symbols

**Why Synthetic is Okay:**
Tool selection is relatively straightforward. The signatures and use cases are clear. Synthetic examples capture the basics well enough.

**Example Gap:**
Minimal - the 1/5 failure is likely noise or an edge case. LSP tools are working as intended for most queries.

**Data Collection Strategy:**
- Log LSP tool selection decisions
- Capture natural language patterns for each tool
- Track success/failure rates per tool
- Record edge cases where tool selection was wrong

---

## Overall Verdict

| Area | Current | Target | Impact | Reason |
|------|---------|--------|--------|--------|
| **Cross-tool workflows** | 0% | 60%+ | **REALLY BIG 🔥** | Complete gap in multi-step patterns |
| **Field access** | 60% | 80%+ | **BIG 🔥** | Real usage patterns unknown |
| **New LSP tools** | 80% | 90%+ | **MEDIUM 🟡** | Already mostly working |

---

## What Real-World Data Captures That Synthetic Can't

### Synthetic Examples Are Good For:
- ✅ Teaching tool signatures and types
- ✅ Showing field structures
- ✅ Basic "hello world" examples
- ✅ Demonstrating syntax

### Real-World Data Is Critical For:
- 🔥 **Sequencing:** Which tools go together and in what order
- 🔥 **Judgment:** When to use one tool vs another
- 🔥 **Natural patterns:** How users actually phrase requests
- 🔥 **Dependencies:** Using tool1 results to inform tool2 calls
- 🔥 **Relevance:** Which fields/features actually matter in practice
- 🔥 **Conditional logic:** If/else decisions based on tool results
- 🔥 **Context awareness:** Tool selection based on conversation context

---

## Recommended Data Collection Strategy

### Priority 1: Cross-Tool Workflows (REALLY BIG Impact)

**What to capture:**
- ANY instance of user requesting multiple operations in one query
- Tool sequence executed (with timestamps)
- Intermediate results and how they influenced next tool
- Natural language phrasing of the request
- Success/failure of the workflow

**Collection points:**
- User queries containing "and", "then", "after", "if"
- Queries resulting in multiple tool calls
- Sessions with 2+ consecutive tool calls
- User feedback on multi-step responses

**Example logs:**
```json
{
  "query": "check git status and if there are changes, diff them",
  "tools_called": ["git_status", "git_diff"],
  "decision_point": "status_result.clean == False",
  "success": true,
  "user_feedback": "helpful"
}
```

### Priority 2: Field Access Patterns (BIG Impact)

**What to capture:**
- Which result fields are accessed in generated code
- Conditional logic using field values
- Iteration patterns (full, limited, filtered)
- Field access frequency distribution

**Collection points:**
- Code execution logs showing field access
- User queries asking about specific result fields
- Error logs when accessing missing/null fields
- User corrections/refinements based on results

**Example logs:**
```json
{
  "tool": "ruff_check",
  "fields_accessed": ["violation_count", "violations"],
  "access_pattern": "count_then_iterate",
  "iteration_limit": 5,
  "conditional": "if violation_count > 0"
}
```

### Priority 3: LSP Tool Selection (MEDIUM Impact)

**What to capture:**
- LSP tool selection decisions and context
- Natural language patterns per tool
- Success/failure rates
- Edge cases and errors

**Collection points:**
- Queries mentioning "hover", "definition", "references", "symbols"
- Tool selection with confidence scores
- User corrections ("no, I meant hover not goto")
- Disambiguation requests

---

## Implementation: The Flywheel

### Phase 1: Capture
1. **Instrument the system:**
   - Log all queries and tool calls
   - Track field access in generated code
   - Record user feedback (thumbs up/down, corrections)

2. **Privacy-preserving collection:**
   - Hash sensitive data (file paths, symbols)
   - Aggregate patterns, not raw data
   - User opt-in for data collection

### Phase 2: Analyze
1. **Extract patterns:**
   - Common tool sequences
   - Field access frequency
   - Natural language patterns

2. **Identify gaps:**
   - Where model fails most often
   - Which patterns are missing from training data
   - What users ask for that model can't do

### Phase 3: Generate
1. **Create training examples from real usage:**
   - Convert logs to training format
   - Preserve natural language patterns
   - Include context and decision logic

2. **Balance dataset:**
   - Mix real-world + synthetic
   - Weight by frequency of use
   - Cover edge cases

### Phase 4: Train
1. **Incremental improvement:**
   - Add real-world examples to training set
   - Retrain periodically
   - Validate on held-out real data

2. **Measure impact:**
   - Track accuracy on real queries over time
   - Monitor field access success rates
   - Measure cross-tool workflow success

### Phase 5: Deploy & Repeat
- Deploy improved model
- Continue collecting data
- **Flywheel effect:** Better model → better responses → better data → better model

---

## Expected Outcomes

### With Real-World Data Collection:

**Cross-tool workflows:**
- 0% → 60-70% success rate
- Model learns real workflow patterns
- Natural sequencing and dependencies

**Field access:**
- 60% → 80-85% success rate
- Consistent field usage
- Appropriate iteration patterns

**Overall model quality:**
- 72% → 80-85% honest accuracy
- Better user satisfaction
- More natural responses

### Without Real-World Data Collection:

**Status quo:**
- Cross-tool remains broken (0%)
- Field access stays inconsistent (60%)
- Overall stagnates at 72%
- Synthetic examples hit diminishing returns

---

## Conclusion

Real-world data collection would have transformative impact on the areas where the model currently fails. The flywheel approach (capture → analyze → generate → train → deploy → repeat) turns usage into improvement, making the model progressively better at what users actually need.

**Investment priority:**
1. **Highest ROI:** Cross-tool workflow capture (0% → 60%+ gain)
2. **High ROI:** Field access pattern capture (60% → 80%+ gain)
3. **Medium ROI:** LSP tool selection refinement (80% → 90%+ gain)

The gap between synthetic and real-world data is largest for behaviors requiring judgment, sequencing, and context-awareness - exactly what's failing now.

---

## Critical Learnings from Audit: What Data Actually Proves Flywheel Value

The Phase 27.5 audit and earlier phases revealed crucial insights about what data is needed to validate and improve "code tools" AI systems. These learnings directly inform the Flywheel approach.

### 1. Quality Over Quantity: The 345 Junk Examples Problem

**What we learned:**
Phase 27.5 added 345 "new" training examples, but analysis revealed:
- ~330 were repetitive junk (loops with only index changing)
- ~8-13 were genuinely useful
- Many had bugs (grep always searches for "TODO", "git git" command bug)
- 45 were vacuous ("Explain concept 14" → "Concept 14 is about...")

**Impact on Flywheel:**
- **Bad data is worse than no data** - it teaches wrong patterns
- **Volume metrics lie** - "345 new examples!" sounds good but was net negative
- **Quality signals are essential** - need to filter/validate collected data

**What data is needed:**
- ✅ **User success signals:** Did the response solve the problem?
- ✅ **Correction signals:** Did user rephrase or clarify after response?
- ✅ **Completion signals:** Did user continue the workflow or abandon?
- ❌ **Raw volume:** Number of examples collected is meaningless
- ✅ **Diversity metrics:** Are we collecting new patterns or duplicates?

**Flywheel implication:** Need quality gates BEFORE adding data to training set. Raw usage logs ≠ training data.

---

### 2. Validation Must Check Actual Behavior

**What we learned:**
Phase 27.5 original validation:
```python
success = len(response) > 10 and not response.startswith("Error")
```
This gave 78% accuracy but was **meaningless** - just checked if model said anything.

Fixed validation checking actual tool calls:
```python
success = all(f"{tool}(" in response for tool in expected_tools)
```
This gave 72% honest accuracy - revealing the true state.

**Impact on Flywheel:**
- **Vanity metrics hide problems** - "improving" from 75% → 78% → 80% on broken validation means nothing
- **Behavior testing > output testing** - must verify WHAT the model does, not just that it responds
- **False confidence is dangerous** - team thought Phase 27.5 was production-ready at "78%"

**What data is needed:**
- ✅ **Tool call traces:** Which tools were actually invoked, in what order
- ✅ **Field access patterns:** Which result fields were accessed in generated code
- ✅ **Execution outcomes:** Did the code run successfully? Any errors?
- ✅ **User verification:** Did user confirm the result was correct?
- ❌ **Response length:** Meaningless proxy metric
- ❌ **Keyword presence:** "result.error_count" in response doesn't mean it was used correctly

**Flywheel implication:** Need execution-level telemetry, not just text analysis. Must log what code DOES, not just what it says.

---

### 3. The Infrastructure vs Behavior Gap

**What we learned:**
Phase 27.5 infrastructure testing showed:
- ✅ ty supports all LSP capabilities (hoverProvider, documentSymbolProvider, etc.)
- ✅ Parsers work correctly on hand-crafted JSON
- ✅ Async bridges function properly
- ✅ All 582 unit tests pass

But behavioral testing revealed:
- ❌ Model still fails 20% of new LSP queries
- ❌ Cross-tool workflows: 0% success
- ❌ Field access: inconsistent (60%)

**The gap:** Infrastructure working ≠ model knows how to use it

**Impact on Flywheel:**
- **Unit tests don't predict usage** - all tests green, but model can't use tools
- **Capability ≠ Competence** - having the tool doesn't mean knowing when/how to use it
- **Integration testing is critical** - must test model behavior end-to-end

**What data is needed:**
- ✅ **End-to-end success rates:** User query → tool execution → user satisfaction
- ✅ **Failure mode analysis:** WHEN does model choose wrong tool or wrong sequence?
- ✅ **Context patterns:** What user context leads to successful vs failed tool selection?
- ✅ **Real usage patterns:** How do users ACTUALLY phrase requests for each tool?
- ❌ **Infrastructure metrics alone:** Parser tests, server uptime, API response times
- ❌ **Static analysis:** Code coverage, type safety without runtime behavior

**Flywheel implication:** Must collect real usage data, not just infrastructure metrics. The model's behavior in the wild is what matters.

---

### 4. The git_log Bug: When Training Data Lies

**What we learned:**
The `git_log` tool had a critical bug:
- Command: `git log --oneline` (doesn't include author/date)
- Stubs claimed: `commit.author` and `commit.date` exist and are populated
- Training data showed: Examples accessing these fields
- **Reality:** All commits had `author=None, date=None`

**Result:** 100% of git_log training examples were teaching the model to access fields that are always None.

**Impact on Flywheel:**
- **Synthetic data can be systematically wrong** - generated examples matched stubs, but stubs were wrong
- **Unit tests with mocks hide bugs** - hand-crafted test data had author/date, real output didn't
- **Model learns from broken examples** - "if it's in training data, it must be right"
- **Silent failures are invisible** - accessing None fields doesn't raise errors, just returns None

**What data is needed:**
- ✅ **Real execution traces:** Actual tool outputs, not mocked/stubbed data
- ✅ **Field value distributions:** Are fields actually populated? With what values?
- ✅ **Null/error rates:** How often are fields None or cause errors?
- ✅ **User complaints:** "The git log doesn't show authors" → bug signal
- ✅ **Integration tests with real services:** Test against actual git, not mocks
- ❌ **Hand-crafted test data:** Doesn't match reality
- ❌ **Stub-based training:** Assumes API contracts match reality

**Flywheel implication:** MUST validate training data against real tool outputs. Synthetic examples need ground truth verification.

---

### 5. Train/Test Consistency: The 60-Point Accuracy Drop

**What we learned:**
Phase 26.1 validation bug:
- Training data used tokenizer's ChatML format: `<|im_start|>user\n...<|im_end|>`
- Validation script used plain text: `"User: {query}\nAssistant:"`
- **Result:** Model trained on one format, tested on another
- **Impact:** 60-point accuracy drop (28% → 88%) due to format mismatch alone

After fixing format to match training:
- Same model, same queries
- Only change: validation prompt format
- **Result:** 88% accuracy (vs 28% with wrong format)

**Impact on Flywheel:**
- **Format consistency is critical** - train/test/production must use EXACT same format
- **Small mismatches have huge impact** - prompt format difference = 60 points
- **Infrastructure matters** - not just data, but how it's presented to model
- **False negatives hide progress** - model was good, validation was broken

**What data is needed:**
- ✅ **Format-aware collection:** Capture data in production format (ChatML, XML, etc.)
- ✅ **Consistency verification:** Ensure train/valid/prod use same formatting
- ✅ **Format metadata:** Log which prompt format was used for each query
- ✅ **A/B format testing:** Test same queries with different formats to detect issues
- ❌ **Format-agnostic logs:** Raw text without formatting metadata
- ❌ **Post-hoc reformatting:** Converting logs to training format (introduces errors)

**Flywheel implication:** Capture data in the EXACT format the model will see in production. Format is part of the data.

---

### 6. Single-Tool Training ≠ Multi-Tool Behavior

**What we learned:**
Phase 27.5 training data:
- 1000+ examples of single-tool usage (ruff, pytest, typecheck individually)
- 50 examples claiming to show "multi-tool workflows"
- **Result:** Model learned single tools perfectly, but 0% success on cross-tool

**Analysis revealed:**
- Multi-tool examples didn't actually show ALL tools being called
- Examples showed intent ("run all quality checks") but not execution (only called one tool)
- Model learned: "when user says multiple tools, pick the most relevant one"

**Impact on Flywheel:**
- **Emergent behavior doesn't emerge** - can't assume model will combine skills
- **Explicit demonstration required** - must show actual multi-step execution
- **Intent ≠ Implementation** - query says "do A and B" but code only does A
- **Compositional learning is hard** - knowing A and knowing B doesn't mean knowing A→B

**What data is needed:**
- ✅ **Complete execution traces:** Full tool call sequence with intermediate results
- ✅ **Decision points:** Why was tool2 called after tool1? What data informed the decision?
- ✅ **State transitions:** tool1 result → model reasoning → tool2 call
- ✅ **Failure recovery:** User asks for A+B, model does A, user says "also do B"
- ❌ **Intent-only data:** Queries mentioning multiple tools without seeing execution
- ❌ **Single-tool examples alone:** No matter how many, won't teach sequencing

**Flywheel implication:** For multi-step workflows, must capture the FULL sequence including intermediate reasoning/decisions.

---

### 7. Discrimination Success Proves Data Quality Works

**What we learned:**
Tool vs direct-answer discrimination:
- Phase 27.5: 100% accuracy (5/5)
- Model perfectly distinguishes:
  - "What is LSP hover?" → direct answer
  - "Show hover for UserService" → tool call

**Why it worked:**
- Training data had clear examples of both patterns
- 33% of examples were direct answers (good balance)
- Examples showed contrast: concept questions vs action requests

**Impact on Flywheel:**
- **Proof that good data works** - with right examples, model learns perfectly
- **Balance matters** - 33% direct answers created clear discrimination
- **Contrast learning** - showing both "do this" and "don't do this" helps
- **Quality over quantity** - 50 good discrimination examples > 500 ambiguous ones

**What data is needed:**
- ✅ **Contrastive pairs:** Similar queries with different expected behaviors
- ✅ **Negative examples:** When NOT to use a tool (as important as when to use it)
- ✅ **Boundary cases:** Edge cases between "use tool" and "direct answer"
- ✅ **User corrections:** "No, I don't want to run a tool, just tell me" → negative signal
- ✅ **Balanced distribution:** Equal representation of different behavior types
- ❌ **Only positive examples:** Doesn't teach discrimination
- ❌ **Imbalanced classes:** 90% tool calls, 10% direct answers → bias

**Flywheel implication:** Collect both positive AND negative examples. Success cases AND "don't do this" cases.

---

### 8. Field Access Needs Explicit Demonstration

**What we learned:**
Phase 23 (first typed tools):
- Added TypeCheckResult with `error_count`, `errors` fields
- Training showed tool calls: `result = typecheck("src/")`
- **But** only 5% of examples accessed result fields
- **Result:** Model called tools but didn't use structured results (0% field access)

Phase 26 (field access training):
- Added 120 examples explicitly showing field access: `if result.error_count > 0:`
- Increased field access examples from ~5% to ~22% of dataset
- **Result:** 92% accuracy, 90% field access rate

**Impact on Flywheel:**
- **Implicit knowledge doesn't transfer** - model won't guess to access fields
- **Demonstration is required** - must show code accessing fields
- **Pattern frequency matters** - 5% examples insufficient, 22% works
- **Structured data needs structured examples** - typed results need typed usage

**What data is needed:**
- ✅ **Field access patterns:** Code that accesses result.field_name
- ✅ **Conditional logic:** if result.error_count > 0: ...
- ✅ **Iteration patterns:** for error in result.errors: ...
- ✅ **Field combinations:** Accessing multiple related fields together
- ✅ **Usage frequency:** Which fields are accessed most often in real code
- ❌ **Tool calls alone:** Calling typecheck() without accessing results
- ❌ **Type signatures alone:** Knowing fields exist doesn't teach usage

**Flywheel implication:** For structured data, must capture HOW users interact with results, not just that tools were called.

---

### 9. Real Testing Reveals What Unit Tests Miss

**What we learned:**
Phase 27.5 audit Priority 1:
- **Unit tests:** All git_log parser tests passing (used hand-crafted JSON)
- **Real testing:** git_log bug discovered (author/date always None)
- **Gap:** Unit test data ≠ real tool output

LSP capability testing:
- **Unit tests:** Parser tests with hand-crafted LSP responses
- **Real testing:** ty server returns responses in correct format
- **Result:** Parsers work, but never tested against real ty output end-to-end

**Impact on Flywheel:**
- **Mocks hide reality** - hand-crafted test data doesn't match real output
- **Integration testing is critical** - must test full stack: model → tool → real service
- **Edge cases live in production** - real data has variations mocks don't capture
- **False confidence from unit tests** - all green, but production fails

**What data is needed:**
- ✅ **Production traces:** Real tool outputs from actual usage
- ✅ **Error cases:** What happens when tools fail in production
- ✅ **Edge cases:** Unusual but real outputs (binary files in git diff, etc.)
- ✅ **Service variations:** Different versions/configs produce different outputs
- ✅ **Integration test results:** Full pipeline success/failure rates
- ❌ **Mock data only:** Clean, ideal examples that don't match reality
- ❌ **Unit test coverage alone:** Doesn't predict production behavior

**Flywheel implication:** Must test and collect data against REAL services. Mocks are useful for development, but training needs production reality.

---

### 10. Metrics Must Measure What Matters

**What we learned:**
Phase 27.5 metrics evolution:

**Bad metrics:**
- `len(response) > 10` → 78% (meaningless)
- "Did model respond?" → 100% (vacuous)
- Token count, response time → doesn't measure correctness

**Better metrics:**
- "Did model call expected tools?" → 72% (honest)
- "Did model access result fields?" → 60% (reveals gaps)
- "Did cross-tool workflows succeed?" → 0% (critical failure mode found)

**Best metrics (not yet implemented):**
- "Did user achieve their goal?" → real success measure
- "Did user correct the response?" → error signal
- "Time to task completion" → efficiency measure

**Impact on Flywheel:**
- **Wrong metrics drive wrong improvements** - optimizing for 78% on broken validation
- **Honest metrics reveal gaps** - 0% cross-tool shows where to focus
- **User-centric metrics matter most** - did the tool help the user?
- **Proxy metrics mislead** - response length ≠ quality

**What data is needed:**
- ✅ **Task completion signals:** Did user finish what they started?
- ✅ **User corrections:** User edits model output → it was wrong
- ✅ **Abandonment signals:** User gave up → major failure
- ✅ **Follow-up queries:** "No, I meant..." → model misunderstood
- ✅ **Positive feedback:** Thumbs up, "thanks", continued workflow → success
- ✅ **Behavioral metrics:** Tools called correctly, fields accessed, workflows completed
- ❌ **Text-only metrics:** Response length, keyword presence
- ❌ **Vanity metrics:** "Model responded fast" doesn't mean it helped

**Flywheel implication:** Instrument for user success signals, not just system outputs. The goal is helping users, not generating text.

---

## Summary: Data Requirements for Flywheel Validation

Based on audit learnings, the Flywheel approach requires:

### Must-Have Data:

1. **Complete execution traces:**
   - Full tool call sequences with intermediate results
   - Decision points and reasoning
   - Field access patterns in generated code
   - Success/failure outcomes

2. **User feedback signals:**
   - Task completion (user achieved goal)
   - Corrections (user edited output)
   - Abandonment (user gave up)
   - Follow-ups (user clarified intent)
   - Positive confirmation (thumbs up, continued workflow)

3. **Real-world outputs:**
   - Actual tool responses (not mocks)
   - Edge cases and errors from production
   - Service variations (different configs, versions)
   - Integration test results

4. **Format-consistent collection:**
   - Data in production format (ChatML, XML, etc.)
   - Prompt structure preserved
   - Metadata about formatting

5. **Quality gates:**
   - Filter bad examples before training
   - Validate against ground truth
   - Check for bugs in synthetic data
   - Verify diversity (not repetitive)

### Critical Metrics:

1. **Behavioral accuracy:**
   - Tool selection correctness
   - Field access rate
   - Cross-tool workflow success
   - End-to-end task completion

2. **User satisfaction:**
   - Goal achievement rate
   - Correction frequency
   - Abandonment rate
   - Positive feedback rate

3. **System health:**
   - Tool execution success rate
   - Error rates by tool
   - Response times
   - Field null rates (data quality)

### Data Collection Anti-Patterns to Avoid:

❌ **Volume without quality** - 345 examples, 330 junk
❌ **Mocks instead of reality** - hand-crafted test data
❌ **Text analysis without execution** - checking response length
❌ **Intent without implementation** - queries mentioning tools but not showing usage
❌ **Single-tool examples expecting multi-tool learning** - composition doesn't emerge
❌ **Format-inconsistent collection** - train on one format, test on another
❌ **Vanity metrics** - fast responses that don't help users
❌ **Infrastructure metrics alone** - tests passing but model failing

---

## Flywheel Validation Checklist

To prove the Flywheel approach works, collect and measure:

- [ ] Real tool call sequences from production (not synthetic)
- [ ] User success signals (completion, feedback, corrections)
- [ ] Full execution traces (tools + fields + decisions)
- [ ] Format-consistent data (same as production)
- [ ] Quality-filtered examples (validated against ground truth)
- [ ] Behavioral accuracy metrics (not just text metrics)
- [ ] Integration test results (real services, not mocks)
- [ ] Cross-tool workflow success rate (not just single-tool)
- [ ] Field access patterns in generated code
- [ ] User satisfaction metrics (goal achievement, not response time)

**The Flywheel works when:** Adding real usage data → improves behavioral accuracy → increases user success → generates better usage data → cycle repeats.

**The Flywheel fails when:** Collecting low-quality data → metrics don't improve → users don't benefit → no flywheel effect.

---

## Beyond Tool Calls — Capturing Complete Problem-Solving Episodes

The current data collection thinking is tool-call-level: "did the model call `ruff_check()`?" The deeper insight is that the **unit of learning is the complete problem-solving episode** — from spec to shipped feature.

### Three Layers of Data Capture

**Layer 1: Tool traces (what we have today — synthetic)**
- Individual tool calls and results
- "Call `typecheck("src/")` → receives TypeCheckResult"
- Captures WHAT tools exist and WHAT they return
- Good for: Teaching tool signatures, field structures, basic examples

**Layer 2: Interaction sessions (what to build next — real)**
- Multi-prompt conversations including user corrections, follow-ups, decision points
- "User: 'check types' → Model: calls typecheck → User: 'also lint' → Model: calls ruff_check → User: 'perfect'"
- Captures HOW tools are used together, WHEN to use one vs another, WHY a sequence matters
- Good for: Cross-tool workflows, field access patterns, natural language understanding, decision-making

**Layer 3: Feature episodes (the vision — complete)**
- Complete spec → branch → implementation → validation → merge cycles
- "Spec: Add user auth → Branch: feature/auth → 15 prompts → 8 tool calls → 12 commits → tests pass → merged"
- Captures END-TO-END problem-solving patterns, WORKFLOW structure, SUCCESS criteria
- Good for: Learning what works in practice, understanding context dependencies, measuring outcomes

**Key insight:** Layer 1 teaches vocabulary. Layer 2 teaches conversation. Layer 3 teaches problem-solving.

### Why This Matters: The Phase 27.5 Evidence

**Current state (Layer 1 only):**
- 1104 synthetic examples teach individual tool usage
- Model learns: "`typecheck()` checks types", "`git_diff()` shows changes"
- **But fails at:** Using tools in sequence (0% cross-tool), knowing when fields matter (60% field access)

**What Layer 2 would reveal:**
- Real users say "check if tests pass, if not lint the failing files" (conditional sequencing)
- Real users say "review the changes" (implicit = `git_diff` + `read_file`)
- Real users correct "no, use hover not goto_def" (discrimination signals)

**What Layer 3 would capture:**
- Complete feature branch: 15 prompts about auth system implementation
- Every decision point: "should this be middleware or service?" → "service" → successful merge
- Ground truth: Code shipped to production, tests pass, no rollbacks

**The gap:** We're teaching words (Layer 1) but not sentences (Layer 2) or stories (Layer 3).

---

## Multi-Prompt Interaction Capture

Design for capturing what happens across multiple prompts, not just single tool calls.

### Conversation Structure Elements

**1. Decision Trees**
```
Turn 1: User: "check git status"
        Model: calls git_status() → finds staged files
Turn 2: Model: "You have staged files. Want to see the diff?"
        User: "yes"
Turn 3: Model: calls git_diff(staged=True) → shows changes
        User: "looks good"
```

**Key capture:** Model made a decision based on tool1 result (status.staged_count > 0) to suggest tool2 (diff). This is gold for cross-tool training.

**2. Refinement Chains**
```
Turn 1: User: "show hover for UserService"
        Model: calls hover() → shows type info
        User: "also show the author"
Turn 2: Model: calls git_log() → adds commit info
        User: "perfect"
```

**Key capture:** Progressive improvement. User's "also" signals the first response was incomplete but on-track. "Perfect" signals completion.

**3. Abandonment Signals**
```
Turn 1: User: "find all components"
        Model: calls workspace_symbols(query="component")
Turn 2: User: "no, I meant tdom components"
        Model: calls grep(pattern="@view")
Turn 3: User: "forget it, I'll do it manually"
```

**Key capture:** Two failed attempts → user gave up. This is a **strong negative signal** worth 10x a success. The model failed to understand "tdom components" means `@view` decorator.

**4. Context Carryover**
```
Turn 1: User: "what files changed?"
        Model: calls git_diff() → lists files
Turn 2: User: "lint those files"
        Model: calls ruff_check() on the file list from Turn 1
```

**Key capture:** "Those files" refers to tool1 results. This is how cross-tool patterns emerge — tool2 arguments come from tool1 outputs.

### Concrete JSONL Schema

```json
{
  "session_id": "2026-02-16-abc123",
  "start_time": "2026-02-16T10:30:00",
  "end_time": "2026-02-16T10:35:45",
  "outcome": "success",
  "turns": [
    {
      "turn_number": 1,
      "user_message": "check git status and if there are changes, diff them",
      "model_response": {
        "reasoning": "User wants conditional: status → if changes → diff",
        "tool_calls": [
          {
            "tool": "git_status",
            "args": {"path": "."},
            "result": {
              "type": "GitStatusResult",
              "clean": false,
              "staged_count": 3,
              "unstaged_count": 5
            }
          },
          {
            "tool": "git_diff",
            "args": {"path": ".", "staged": false},
            "result": {
              "type": "GitDiffResult",
              "changed_files": ["src/app.py", "tests/test_app.py"],
              "additions": 45,
              "deletions": 12
            }
          }
        ],
        "response_text": "You have 3 staged and 5 unstaged changes. Here's the diff: ...",
        "field_access": ["clean", "staged_count", "unstaged_count", "changed_files"]
      },
      "user_feedback": {
        "type": "implicit_positive",
        "signal": "continued_workflow",
        "timestamp": "2026-02-16T10:31:30"
      }
    },
    {
      "turn_number": 2,
      "user_message": "lint the changed files",
      "model_response": {
        "reasoning": "User wants ruff_check on files from previous git_diff",
        "context_used": {
          "source": "turn_1.tool_calls[1].result.changed_files",
          "value": ["src/app.py", "tests/test_app.py"]
        },
        "tool_calls": [
          {
            "tool": "ruff_check",
            "args": {"path": "src/app.py"},
            "result": {"type": "RuffResult", "violation_count": 2}
          },
          {
            "tool": "ruff_check",
            "args": {"path": "tests/test_app.py"},
            "result": {"type": "RuffResult", "violation_count": 0}
          }
        ],
        "response_text": "Found 2 lint issues in src/app.py, tests look clean.",
        "field_access": ["violation_count"]
      },
      "user_feedback": {
        "type": "explicit_positive",
        "signal": "thumbs_up",
        "timestamp": "2026-02-16T10:32:15"
      }
    }
  ],
  "metadata": {
    "total_turns": 2,
    "total_tool_calls": 4,
    "cross_tool_dependencies": 1,
    "user_satisfaction": "positive",
    "completion_reason": "task_complete"
  }
}
```

**Why this schema:**
- Captures full conversation context, not just isolated tool calls
- Records `context_used` to show cross-tool data flow
- Tracks `user_feedback` at each turn (implicit and explicit)
- Includes `field_access` to measure structured result usage
- Stores `outcome` and `completion_reason` for quality signals

### Collection Implementation

**Where to hook:**
1. **Session start:** Generate session_id, start timer
2. **Each user message:** Record as new turn
3. **Each model response:** Record tool calls, field access, response text
4. **Each user reaction:** Detect feedback signals (continue, correct, abandon)
5. **Session end:** Compute metadata, write JSONL

**Key storage decision:** One JSONL line per session (not per turn). This preserves conversational structure.

---

## User Quality Signals

Design lightweight quality feedback that doesn't interrupt workflow.

### Inline Signals (Automatic, No User Action)

**1. Continuation = Positive**
```
User: "check types"
Model: calls typecheck() → shows errors
User: "now lint" ← Implicit positive: user continued workflow
```

**Signal strength:** Medium. User didn't complain, but didn't confirm either.

**2. Correction = Negative**
```
User: "show hover for UserService"
Model: calls goto_definition() ← WRONG TOOL
User: "no, I wanted hover, not goto" ← Explicit negative: model misunderstood
```

**Signal strength:** Strong. User explicitly said model was wrong.

**3. Abandonment = Strong Negative**
```
User: "find all async functions"
Model: calls grep(pattern="async") ← Too broad
User: [5 minutes pass, no follow-up] ← User gave up
```

**Signal strength:** Very strong. User walked away = major failure.

**4. Refinement = Weak Negative**
```
User: "check git status"
Model: calls git_status() → shows output
User: "also show the diff" ← Partial positive: model started right, but incomplete
```

**Signal strength:** Weak negative. Model was on-track but didn't anticipate next need.

### Explicit Rating (Optional, Low Friction)

**After each response:**
```
Model: [shows result]
UI: [👍] [👎] [Skip]
```

**If user clicks 👍:** Record positive, boost training weight
**If user clicks 👎:** Record negative, maybe prompt: "What went wrong?"
**If user skips:** Use implicit signals only

**Implementation:**
- Show thumbs only for tool-calling responses (not direct answers)
- Fade after 3 seconds if no interaction
- Don't block workflow — completely optional

### Correction Capture

**When user rephrases:**
```
Turn 1: User: "show me the function"
        Model: calls read_file("src/app.py") ← Wrong interpretation
Turn 2: User: "no, show me the function definition for 'process_payment'"
        Model: calls goto_definition(symbol="process_payment") ← Correct
```

**Capture as contrastive pair:**
- Negative example: Query "show me the function" → read_file (WRONG)
- Positive example: Query "show function definition for X" → goto_definition (RIGHT)

**Training value:** Teaches discrimination. Similar queries, different intents.

### Outcome Tracking

**Feature branch outcomes:**
1. **Did the branch merge?**
   - Merged → strong positive signal for all interactions in that branch
   - Closed without merge → negative signal
   - Still open → neutral (incomplete)

2. **Did validation pass?**
   - `ruff_check` → 0 violations at merge time → positive
   - `pytest_run` → all tests pass → positive
   - `typecheck` → no errors → positive
   - Any failing at merge → mixed signal (shipped despite issues)

3. **Was there a rollback?**
   - No rollback in 7 days → strong positive
   - Rollback within 24h → strong negative (shipped bad code)

**Capture strategy:**
```json
{
  "branch": "feature/user-auth",
  "interactions": 15,
  "tool_calls": 42,
  "outcome": {
    "merged": true,
    "ruff_violations_at_merge": 0,
    "pytest_pass_rate": 1.0,
    "typecheck_errors": 0,
    "rollback_within_7d": false
  },
  "quality_score": 1.0
}
```

**Use for filtering:** Only train on interactions from branches with `quality_score >= 0.8`.

### The Best Signal: What Happens Next

**Truth table:**

| User Action After Response | Signal | Interpretation |
|----------------------------|--------|----------------|
| Continues workflow | Positive | Model helped |
| Says "perfect" / "thanks" | Strong positive | Model nailed it |
| Asks clarification | Neutral | Response unclear |
| Rephrases query | Weak negative | Model misunderstood |
| Says "no, I meant..." | Strong negative | Model was wrong |
| Gives up / switches tasks | Very strong negative | Model failed completely |
| Edits model output | Weak negative | Close but needs fixes |
| Accepts output as-is | Strong positive | Model was correct |

**Implementation:** Track time between responses, classify next user message, compute signal strength.

---

## Spec-Driven Feature Branch Episodes

Punie's architecture (agent-os specs → feature branches) creates a unique data collection opportunity: complete episodes with ground truth.

### What Makes This Special

**Traditional data collection:**
- Logs individual queries: "check types" → called `typecheck()` → isolated example
- No context about why the user asked or what happened after
- No ground truth about whether the overall goal succeeded

**Spec-driven episodes:**
- A **spec** defines the goal: "Add user authentication with JWT tokens"
- A **feature branch** captures the entire journey: 15 prompts, 42 tool calls, 12 commits
- The **git history** shows what was actually written and how it evolved
- The **validation results** show whether quality gates passed at each stage
- The **merge/close event** is the ground truth: did it ship?

**Why this matters:** You get complete supervised learning episodes with outcome labels.

### Episode Structure

```json
{
  "episode_id": "feature/user-auth-2026-02-16",
  "spec": {
    "title": "Add user authentication system",
    "file": "agent-os/specs/2026-02-16-user-auth/spec.md",
    "requirements": [
      "JWT token generation",
      "Login endpoint",
      "Protected routes middleware",
      "User session management"
    ],
    "acceptance_criteria": [
      "Users can log in with email/password",
      "JWT tokens expire after 24h",
      "Protected routes return 401 if no token",
      "All tests pass"
    ]
  },
  "branch": {
    "name": "feature/user-auth",
    "created": "2026-02-16T09:00:00",
    "merged": "2026-02-16T16:45:00",
    "commits": 12,
    "files_changed": 8
  },
  "conversations": [
    {
      "session_id": "session-001",
      "start": "2026-02-16T09:15:00",
      "turns": 5,
      "tool_calls": 8,
      "outcome": "created JWT service"
    },
    {
      "session_id": "session-002",
      "start": "2026-02-16T10:30:00",
      "turns": 7,
      "tool_calls": 12,
      "outcome": "added login endpoint + tests"
    },
    {
      "session_id": "session-003",
      "start": "2026-02-16T14:00:00",
      "turns": 3,
      "tool_calls": 5,
      "outcome": "added middleware for protected routes"
    }
  ],
  "validation_checkpoints": [
    {
      "timestamp": "2026-02-16T12:00:00",
      "ruff_violations": 3,
      "typecheck_errors": 1,
      "pytest_passed": 8,
      "pytest_failed": 2
    },
    {
      "timestamp": "2026-02-16T16:30:00",
      "ruff_violations": 0,
      "typecheck_errors": 0,
      "pytest_passed": 15,
      "pytest_failed": 0
    }
  ],
  "outcome": {
    "status": "merged",
    "all_requirements_met": true,
    "all_acceptance_criteria_met": true,
    "final_validation_passed": true,
    "rollback_within_7d": false
  },
  "quality_score": 1.0
}
```

### Training Data From Episodes

**What to extract:**

**1. Episode-level metadata:**
- Spec requirements → Expected tool calls (e.g., "JWT generation" → likely needs service creation)
- Acceptance criteria → Validation patterns (e.g., "all tests pass" → final `pytest_run()`)
- Outcome → Quality label (merged + no rollback = positive example)

**2. Turn-level traces:**
- Each prompt → tool call → result sequence
- Decision points: "Should I create service or middleware?" → Model chose service → Worked (merged)
- Corrections: "Actually make it middleware" → Model adapted → Worked

**3. Quality signals:**
- Early validation failures → Late validation passes (shows learning/correction)
- User corrections → Model adjustments → Success (shows adaptation)
- Spec requirements → Code artifacts → Tests pass (shows goal achievement)

**Example training sequence:**

```
System: You are Punie, expert in tdom-svcs architecture...

User: I need to implement this spec: [spec.md content]
      Requirements: JWT token generation, login endpoint, protected routes

Model: I'll start by creating a JWT service for token generation.
       result = generate_artifact(
           artifact_type="service",
           name="JWTService",
           code="""
           class JWTService:
               def generate_token(self, user_id: int) -> str:
                   payload = {"user_id": user_id, "exp": datetime.now() + timedelta(days=1)}
                   return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
           """
       )

User: Good! Now add the login endpoint.

Model: I'll create a login view that uses the JWT service.
       result = generate_artifact(
           artifact_type="view",
           name="login_view",
           code="""
           @view
           def login_view(email: str, password: str, *, auth_service: AuthService, jwt_service: JWTService) -> Element:
               user = auth_service.authenticate(email, password)
               if user:
                   token = jwt_service.generate_token(user.id)
                   return html(t'<div>Login successful. Token: {token}</div>')
               return html(t'<div>Login failed</div>')
           """
       )

[... 3 more turns ...]

Outcome: Branch merged, all tests pass, no rollback
Quality: 1.0 (positive example)
```

**Training value:**
- Spec-to-implementation pattern: Requirements → Tool sequence → Working code
- Multi-step problem solving: Service → View → Middleware (correct sequence)
- Domain knowledge: JWT service before login endpoint (logical dependency)
- Quality label: Merged + tests pass = successful pattern

### Benefits of Episode-Level Collection

**1. Ground truth labels:**
- Merged = successful approach
- Closed without merge = unsuccessful approach
- Rollback = broken approach (strong negative)

**2. Complete context:**
- Why the user asked (the spec)
- What they tried (the conversation)
- How it evolved (the commits)
- Whether it worked (the outcome)

**3. Natural workflows:**
- Not synthetic "run all quality checks"
- Real sequences: "implement feature → tests fail → fix → tests pass"
- Actual decision-making under uncertainty

**4. Domain patterns:**
- Sees how tdom components + svcs services fit together
- Learns project structure conventions (where files go)
- Understands validation checkpoint patterns (when to check quality)

---

## Monty as a Data Collection Engine

Connect to the Monty vision (Level 3-4 in holy-grail-architecture.md) but focus specifically on how Monty becomes a rich data source.

### Monty Recap: Model Generates Tool Code

**Current (Level 2 - Code Mode):**
- Model writes Python code that calls existing tools: `result = typecheck("src/")`
- Tools are pre-defined, model just calls them
- Training data: "User asked X → Model called tool Y"

**Monty (Level 3 - Tool Generation):**
- Model writes domain-specific tool implementations on-demand
- Example: User asks "Create UserProfileView" → Model generates full tdom component code
- Tools validate against schemas (Pydantic models)
- Training data: "User described artifact X → Model generated code Y → Validation passed/failed → Code worked/didn't"

**Self-Improvement (Level 4):**
- Every Monty generation → training example
- Schema validation → automatic quality labels
- ModelRetry loops → error→fix pairs (contrastive learning)
- Continuous fine-tuning → model gets better at generating valid code

### How Monty Creates Training Data

**1. Every generation is a training example:**

```python
# User prompt
"Create a user profile view with avatar, name, and bio"

# Model generates
@view
def user_profile_view(user_id: int, *, user_service: UserService) -> Element:
    user = user_service.get(user_id)
    return html(t'''
        <div class="user-profile">
            <img src="{user.avatar_url}" alt="{user.username}"/>
            <h2>{user.username}</h2>
            <p>{user.bio}</p>
        </div>
    ''')

# Validation passes
✓ Syntax valid
✓ Has @view decorator
✓ Returns Element
✓ Uses html(t"...")
✓ Type check passes

# Result: POSITIVE TRAINING EXAMPLE
```

**Training data captured:**
- Prompt: Natural language description
- Generated code: Full implementation
- Validation result: All checks passed
- Outcome: Code saved and works
- Quality label: 1.0 (success)

**2. Schema validation provides quality labels:**

```python
class TdomComponentSchema(BaseModel):
    code: str
    name: str

    @field_validator("code")
    def validate_structure(cls, code: str) -> str:
        # Check @view decorator
        if not has_view_decorator(code):
            raise ValueError("Missing @view decorator")
        # Check return type
        if not returns_element(code):
            raise ValueError("Must return Element")
        # ... more checks
        return code
```

**Quality signals from validation:**
- Passed all checks → Quality score: 1.0
- Failed on decorator → Quality score: 0.0, Error type: "missing_decorator"
- Failed on return type → Quality score: 0.0, Error type: "wrong_return_type"

**Training value:** Automatic labeling. No human annotation needed.

**3. ModelRetry loops capture correction patterns:**

```python
# First attempt (WRONG)
def user_view(user: User) -> str:  # ← Wrong return type
    return str(html(t"<div>{user.name}</div>"))

# Validation fails
ValidationError: "Must return Element, not str"

# Model sees error, retries (CORRECT)
@view  # ← Added decorator
def user_view(user: User) -> Element:  # ← Fixed return type
    return html(t"<div>{user.name}</div>")  # ← Fixed return

# Validation passes
```

**Training data captured:**
- Negative example: First attempt + validation error
- Positive example: Corrected attempt + validation success
- Error→Fix pair: Shows how to fix "wrong return type" error

**Training value:** Contrastive learning. Model learns what NOT to do AND how to fix it.

**4. Domain schemas provide rich validation signals:**

Example schemas from tdom-svcs:
- `TdomComponentSchema`: Checks @view, Element return, html(t"...")
- `ServiceRegistrationSchema`: Checks svcs patterns, DI setup
- `MiddlewareSchema`: Checks ASGI signature, service access
- `TestSchema`: Checks pytest fixtures, assertions

**Each schema provides:**
- Structural rules: "Must have X decorator", "Must return Y type"
- Convention rules: "Name must end with _view", "Use keyword-only args for DI"
- Domain rules: "Components use html()", "Services registered with svcs.register()"

**Validation failures reveal gaps:**
- 60% of generations forget @view → Add more decorator examples to training
- 30% use f-strings instead of t-strings → Add contrastive examples
- 20% make services positional → Emphasize keyword-only pattern

**Data-driven improvement:** Validation metrics → Targeted training data → Better model

### The TrainingCollector in Action

From holy-grail-architecture.md (line 674):

```python
@dataclass
class TrainingCollector:
    """Collect training examples from Monty executions."""

    output_dir: Path

    def record(
        self,
        prompt: str,
        artifact_type: str,
        generated_code: str,
        validation_result: ValidationResult,
        file_path: Path,
    ) -> None:
        """Record a training example."""
        example = {
            "timestamp": datetime.now().isoformat(),
            "artifact_type": artifact_type,
            "user_request": prompt,
            "generated_code": generated_code,
            "validation_passed": validation_result.is_valid,
            "type_check_passed": validation_result.passes_type_check,
            "file_path": str(file_path),
            "metadata": {
                "validation_errors": validation_result.errors,
                "retries": validation_result.retry_count,
            }
        }

        # Append to JSONL
        output_file = self.output_dir / f"monty-traces-{datetime.now():%Y-%m-%d}.jsonl"
        with output_file.open("a") as f:
            f.write(json.dumps(example) + "\n")
```

**But go beyond what the holy-grail doc describes:**

**1. Capture conversation context:**
```python
def record(
    self,
    prompt: str,
    conversation_history: list[Message],  # ← NEW: full context
    artifact_type: str,
    generated_code: str,
    validation_result: ValidationResult,
    file_path: Path,
) -> None:
    example = {
        # ... existing fields ...
        "conversation_context": [
            {"role": msg.role, "content": msg.content}
            for msg in conversation_history[-5:]  # Last 5 turns
        ],
    }
```

**Why:** Prompt alone loses context. "Create a view" might mean tdom component OR Django view. Conversation history disambiguates.

**2. Record which schema rules failed:**
```python
example = {
    # ... existing fields ...
    "validation_errors": [
        {
            "rule": "has_view_decorator",
            "failed": True,
            "error_message": "Missing @view decorator"
        },
        {
            "rule": "returns_element",
            "failed": False
        }
    ],
}
```

**Why:** Knowing WHICH rules fail most often guides training data generation.

**3. Track velocity over time:**
```python
example = {
    # ... existing fields ...
    "generation_time_ms": 450,
    "retry_count": 1,
    "validation_time_ms": 120,
}
```

**Why:** If model gets faster at generating valid code over phases, that's evidence of learning.

**4. Use negative examples as contrastive training:**
```python
def to_training_data(self, examples: list[dict]) -> list[TrainingExample]:
    training_examples = []

    for ex in examples:
        # Add positive examples (validation passed)
        if ex["validation_passed"]:
            training_examples.append(create_positive_example(ex))

        # Add negative examples (validation failed + fix)
        if not ex["validation_passed"] and ex["retries"] > 0:
            training_examples.append(create_negative_example(ex))

    return training_examples
```

**Why:** Showing the model what NOT to do is as valuable as showing what TO do.

### What This Enables

**Phase 27 (current):**
- 1104 synthetic examples
- Model learns tool signatures
- 72% accuracy

**Phase 28 (Monty activated):**
- +100 real Monty generations/week
- +100 validation-labeled examples/week
- +50 error→fix pairs/week
- Model learns domain patterns from usage
- Expected: 75-78% accuracy

**Phase 30 (3 months of collection):**
- +1200 real examples
- Model expert at tdom-svcs patterns
- Expected: 80-85% accuracy
- Velocity: 2-3x faster component generation

**Phase 50 (the vision):**
- +10,000 real examples across all domains
- Model is domain expert, not just code expert
- Expected: 90%+ accuracy
- Velocity: 10x faster than manual coding

---

## What Would Be Fantastic?

Paint the picture of what complete data collection enables.

### 1. Self-Healing Workflows

**Today:**
```
User: "Create UserProfileView"
Model: Generates code with missing @view decorator
Validation: Fails
User: Has to manually fix it
```

**With complete data collection:**
```
User: "Create UserProfileView"
Model: Generates code (Phase 50 weights trained on 500 similar examples)
Validation: Passes first try ✓
User: Ships immediately
```

**How we get there:**
- Collect 500 examples of "missing @view" → "added @view" fixes
- Train on error→fix pairs (contrastive learning)
- Model learns: "When generating tdom component, ALWAYS add @view first"
- Result: 95%+ first-try success rate

### 2. Spec-to-Ship Tracing

**The complete loop:**
```
1. User writes spec: "Add user authentication"
2. Model reads spec → generates plan → implements across 10 files
3. Every prompt → tool call → validation → commit tracked
4. Tests run at checkpoints → Model sees failures → Fixes code
5. Final validation → All pass → Branch merges
6. ENTIRE EPISODE captured as training data

Training data shows:
- Spec requirements → File structures (learns project patterns)
- Implementation sequence → Dependencies (learns "service before view")
- Test failures → Fixes (learns debugging patterns)
- Validation checkpoints → Quality gates (learns when to check)
```

**Result:** Model learns not just code syntax, but problem-solving workflows.

### 3. User-Adaptive Improvement

**Scenario:** User X always corrects hover responses

```
Turn 1: User X: "What does UserService do?"
        Model: calls goto_definition() ← Wrong tool
        User X: "No, hover"

Turn 2: User X: "What does PaymentService do?"
        Model: calls goto_definition() ← Still wrong
        User X: "I said hover!"

Turn 3: User X: "What does AuthService do?"
        Model: calls hover() ← Learned!
        User X: "Perfect"
```

**Data captured:**
- User X has pattern: "What does X do?" → wants hover, not goto_def
- After 3 corrections, model adapts
- Training data weighted by user: User X examples get 2x weight for hover discrimination

**Result:** Personalized model behavior. Learns individual user preferences.

### 4. Cross-Tool Workflow Emergence

**Current state:** 0% cross-tool success (Phase 27.5)

**After capturing 100 real "git diff → read files" sessions:**

```
Session patterns:
- 87% of users: git_diff() → extract file list → read_file() on each
- 62% of users: git_status() → if dirty → git_diff()
- 45% of users: ruff_check() → if violations → read_file() to show context
- 38% of users: git_log() → extract changed files → ruff_check() those files
```

**Training data extracted:**
- "Review the changes" → git_diff() + read_file() sequence (87 examples)
- "Check status and show changes" → git_status() → conditional git_diff() (62 examples)
- "Lint and show errors" → ruff_check() → read_file() for context (45 examples)

**Result after retraining:**
- Cross-tool workflows: 0% → 70% success
- Model learned: "git diff" output contains file paths → use for read_file()
- Model learned: "if violations > 0" → user probably wants to see code

**This is emergent behavior from real data, not synthetic guessing.**

### 5. Domain Knowledge Accumulation

**Every tdom component generated:**
- Adds to corpus of real tdom patterns
- Shows which decorators are common (@view, @component)
- Reveals naming conventions (user_profile_view, not UserProfileView)
- Captures service injection patterns (UserService, AuthService, etc.)

**Every svcs service generated:**
- Shows registration patterns (svcs.register())
- Reveals lifetime management (singleton, request-scoped)
- Captures interface patterns (abstract base classes)

**Every middleware implementation:**
- Shows ASGI signature patterns
- Reveals service access patterns (Container.get())
- Captures error handling patterns

**Result:** Model becomes expert in YOUR domain, not generic Python.

**Phase 27:** Generic Python knowledge + synthetic tdom examples
**Phase 50:** Expert-level tdom-svcs knowledge from 10,000 real implementations

### 6. Quality as a First-Class Signal

**Today:** Quality is a post-hoc check
- Model generates code
- User runs ruff/pytest/typecheck manually
- User tells model "tests fail"
- Model tries to fix

**With quality signals in training:**
```
Model learns:
- Patterns that lead to 0 ruff violations (high quality)
- Patterns that lead to 100% test pass rate (high quality)
- Patterns that get merged without rollback (high quality)

Model internalizes:
- "If I add type hints, typecheck passes" → Always adds type hints
- "If I write pytest fixtures, tests pass" → Generates fixtures upfront
- "If I follow naming conventions, ruff is happy" → Uses conventions automatically
```

**Result:** Model generates high-quality code by default, not by iteration.

### 7. The Complete Data Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERACTION                        │
│  Spec → Conversation → Tool calls → Code → Validation      │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│                   DATA COLLECTION                           │
│  • Multi-turn conversations (Layer 2)                       │
│  • Complete episodes (Layer 3)                              │
│  • Quality signals (user feedback)                          │
│  • Validation results (automatic labels)                    │
│  • Outcome tracking (ground truth)                          │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│                  QUALITY FILTERING                          │
│  • validation_passed = True                                 │
│  • Branch merged successfully                               │
│  • No rollback within 7 days                                │
│  • User satisfaction >= 0.8                                 │
│  • Diversity check (not repetitive)                         │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│                 TRAINING DATA GENERATION                    │
│  • Convert episodes → ChatML format                         │
│  • Add contrastive pairs (error→fix)                        │
│  • Balance dataset (single-tool + cross-tool + direct)      │
│  • Weight by quality score                                  │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│                    FINE-TUNING                              │
│  • Phase N+1 training run                                   │
│  • mlx_lm LoRA (8 layers, 1e-4 lr)                          │
│  • Validate on held-out episodes                            │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────────────┐
│                 DEPLOYMENT & MONITORING                     │
│  • Deploy Phase N+1 model                                   │
│  • Monitor accuracy, velocity, quality                      │
│  • Compare vs Phase N (A/B test)                            │
│  • If better → keep, if worse → rollback                    │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓ (Flywheel repeats)
┌─────────────────────────────────────────────────────────────┐
│           BETTER MODEL → BETTER DATA → ...                  │
│                                                             │
│  Phase 27: 72% accuracy, 1104 synthetic examples            │
│  Phase 30: 78% accuracy, +1200 real examples                │
│  Phase 40: 85% accuracy, +5000 real examples                │
│  Phase 50: 90% accuracy, +10000 real examples               │
│                                                             │
│  Velocity: 1x → 2x → 5x → 10x                               │
└─────────────────────────────────────────────────────────────┘
```

**The flywheel effect:** Each cycle produces a better model, which produces better data, which produces an even better model.

### What Makes This Fantastic vs. Incremental

**Incremental improvement (current approach):**
- Add more synthetic examples
- Hit diminishing returns
- Phase 27 → Phase 28: +2% accuracy
- Synthetic data can't capture real patterns

**Fantastic improvement (data collection approach):**
- Collect real usage data
- Learn actual user patterns
- Phase 27 → Phase 50: +18% accuracy
- Real data reveals what users actually need

**The difference:**
- Incremental: Guessing what patterns matter
- Fantastic: Learning what patterns actually matter in production

### Implementation Checklist

To make this fantastic future real, build:

- [ ] **Multi-prompt session tracking** (Layer 2)
  - Session IDs, turn-by-turn capture
  - Context carryover tracking
  - User feedback detection

- [ ] **Spec-to-branch episode tracking** (Layer 3)
  - Link specs → branches → conversations
  - Track validation checkpoints
  - Record merge/close outcomes

- [ ] **Quality signal collection**
  - Implicit signals (continuation, correction, abandonment)
  - Explicit signals (thumbs up/down)
  - Outcome tracking (merged, tests pass, no rollback)

- [ ] **Monty integration** (Level 3-4)
  - TrainingCollector captures every generation
  - Schema validation provides quality labels
  - ModelRetry loops create error→fix pairs

- [ ] **Filtering and augmentation**
  - Quality gates: only train on successful examples
  - Contrastive pairs: negative examples + fixes
  - Diversity checks: avoid repetitive examples

- [ ] **Continuous training pipeline**
  - Weekly/monthly fine-tuning runs
  - Validation on held-out real data
  - A/B testing before deployment

- [ ] **Metrics dashboard**
  - Accuracy trends over phases
  - Velocity improvements
  - Quality score distributions
  - User satisfaction tracking

**Start small:** Implement Layer 2 (multi-prompt) first, validate it works, then expand to Layer 3 (episodes) and Monty.

**The goal:** By Phase 50, Punie learns from every interaction and gets better every day.

---

## Conclusion

The Phase 27.5 audit revealed that 100% synthetic training data creates critical gaps:
- 0% cross-tool workflows
- 60% field access consistency
- No understanding of real usage patterns

**The solution is three-layered data collection:**

**Layer 1 (current):** Tool traces teach vocabulary — "typecheck() checks types"

**Layer 2 (next):** Interaction sessions teach conversation — "check types, if errors then lint"

**Layer 3 (vision):** Feature episodes teach problem-solving — spec → implementation → validation → merge

**Combined with:**
- User quality signals (what happens next is the best signal)
- Spec-driven episode tracking (ground truth from branch outcomes)
- Monty as data engine (every generation is a training example)
- Continuous improvement (Phase 27 → 30 → 50 → ...)

**The fantastic future:** A self-improving system where every user interaction makes the model better at helping ALL users. Not just a coding assistant, but a learning partner that gets smarter every day.

**Start building it:** Implement multi-prompt tracking first, prove the flywheel works, then expand to full episode collection.
