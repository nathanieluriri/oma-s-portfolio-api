# Fix Plan: Apply Suggestions Conflicts & Corrupted List Fields

## Goal
Make `/portfolios/apply` always replace data (no conflicts), avoid MongoDB update operator conflicts, and prevent corrupted list fields (e.g., `projects` stored as strings) from crashing reads.

## Root Causes
- Mixed `$set` and `$push` on the same list paths caused Mongo conflicts like `contacts.1.label` vs `contacts.1`.
- Incoming update payloads can include both parent list indices (e.g., `contacts[1]`) and child paths (e.g., `contacts[1].label`) in one request.
- Suggestions sometimes send list fields (`projects`, `experience`, etc.) as JSON strings, which can be saved as strings and later crash Pydantic validation.

## Permanent Fixes
1. **Force `$set` only in `/apply`**
   - Remove all `$push` logic in `apply_portfolio_suggestions`.
   - Always use `$set` updates (replacement semantics), even for list indices.

2. **Drop conflicting updates within the same request**
   - If a root list field is updated (e.g., `contacts`), drop all child updates beneath it.
   - If a parent index is updated (e.g., `contacts[1]`), drop all child updates beneath that index (`contacts[1].label`, etc.).

3. **Coerce list fields on write**
   - For list fields (`contacts`, `experience`, `projects`, `skillGroups`), if incoming value is a JSON string, parse it before saving.
   - If parse fails, attempt to extract the JSON array between the first `[` and last `]`.

4. **Normalize list fields on read**
   - In `normalize_portfolio_doc`, coerce list fields when they are strings.
   - On failure, fallback to empty list to prevent 500s on read.

## Expected Request Body (reference)
```
{"updates":[
  {"field":"hero.name","value":"Nathaniel Elo-Oghene Uriri","expectedCurrent":""},
  {"field":"contacts[0]","value":"{\"label\":\"Email\",\"value\":\"nat@uriri.com.ng\",\"href\":\"mailto:nat@uriri.com.ng\"}","expectedCurrent":""},
  {"field":"contacts[1]","value":"{\"label\":\"Phone\",\"value\":\"+2348053964826\",\"href\":\"tel:+2348053964826\"}","expectedCurrent":""},
  {"field":"contacts[2]","value":"{\"label\":\"LinkedIn\",\"value\":\"Nathaniel uriri\",\"href\":\"https://www.linkedin.com/in/nathaniel-uriri\"}","expectedCurrent":""},
  {"field":"contacts[3]","value":"{\"label\":\"GitHub\",\"value\":\"nathanieluriri\",\"href\":\"https://github.com/nathanieluriri\"}","expectedCurrent":""},
  {"field":"resumeUrl","value":"https://example.com/resume.pdf","expectedCurrent":""},
  {"field":"experience[0].role","value":"Head of Product & Innovation","expectedCurrent":""},
  {"field":"experience[0].organization","value":"Digital Guardians","expectedCurrent":""},
  {"field":"experience[0].location","value":"Abuja, Nigeria","expectedCurrent":""},
  {"field":"experience[1].role","value":"Lead Mobile Developer & Product Designer","expectedCurrent":""},
  {"field":"experience[1].organization","value":"Streamz","expectedCurrent":""},
  {"field":"experience[1].location","value":"Abuja, Nigeria","expectedCurrent":""},
  {"field":"projects[0].name","value":"Doux landing page","expectedCurrent":""},
  {"field":"projects[0].location","value":"Abuja, Nigeria","expectedCurrent":""},
  {"field":"projects[0].description","value":"Contributed to the design of a high-impact landing page for Doux, a crypto spending solution, working closely with more experienced designers to refine concepts and improve design quality.","expectedCurrent":""},
  {"field":"contacts[0].label","value":"Email","expectedCurrent":""},
  {"field":"contacts[0].value","value":"nat@uriri.com.ng","expectedCurrent":""},
  {"field":"contacts[0].href","value":"mailto:nat@uriri.com.ng","expectedCurrent":""},
  {"field":"contacts[0].icon","value":"email","expectedCurrent":""},
  {"field":"contacts[1].label","value":"Phone","expectedCurrent":""},
  {"field":"contacts[1].value","value":"+234 (805)-396-4826","expectedCurrent":""},
  {"field":"contacts[1].href","value":"tel:+234 (805)-396-4826","expectedCurrent":""},
  {"field":"contacts[1].icon","value":"phone","expectedCurrent":""}
]}
```

## Notes
- With parent index updates present (e.g., `contacts[0]`), child updates for that index are dropped to avoid conflicts.
- This flow ensures the API always applies updates without conflict checks or push logic.
