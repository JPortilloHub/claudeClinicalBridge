/**
 * Repairs truncated or malformed JSON from LLM outputs.
 *
 * LLM responses frequently get cut off mid-stream due to token limits,
 * producing invalid JSON like:
 *   {"diagnoses": [{"code": "J06.9", "desc
 *   {"plan": [{"actions": ["order CBC", "sche
 *
 * This module attempts progressive repair strategies:
 * 1. Direct parse (already valid)
 * 2. Close unclosed strings, arrays, and objects
 * 3. Strip trailing broken key-value pairs
 * 4. Partial object extraction (grab completed top-level keys)
 */

/**
 * Attempt to parse JSON, repairing truncation if needed.
 * Returns the parsed object or null if unrecoverable.
 */
export function parseJsonSafe(raw: string): unknown | null {
  // Strategy 1: Direct parse
  try {
    return JSON.parse(raw);
  } catch {
    // continue to repair
  }

  // Strategy 2: Repair truncated JSON
  const repaired = repairTruncatedJson(raw);
  if (repaired) {
    try {
      return JSON.parse(repaired);
    } catch {
      // continue
    }
  }

  // Strategy 3: Progressively trim from the end and try closing
  const trimmed = progressiveTrim(raw);
  if (trimmed) {
    try {
      return JSON.parse(trimmed);
    } catch {
      // continue
    }
  }

  // Strategy 4: Extract partial object from completed top-level fields
  const partial = extractPartialObject(raw);
  if (partial) {
    try {
      return JSON.parse(partial);
    } catch {
      // unrecoverable
    }
  }

  return null;
}

/**
 * Repair truncated JSON by closing all open brackets/braces/strings.
 */
function repairTruncatedJson(raw: string): string | null {
  let s = raw.trim();
  if (!s.startsWith('{') && !s.startsWith('[')) return null;

  // Remove trailing comma if present
  s = s.replace(/,\s*$/, '');

  // Remove incomplete key-value: trailing `"key": ` or `"key":` with no value
  s = s.replace(/,?\s*"[^"]*"\s*:\s*$/, '');

  // Remove incomplete string value: `"key": "partial text` (unclosed string as last thing)
  s = s.replace(/,?\s*"[^"]*"\s*:\s*"[^"]*$/, '');

  // Remove incomplete number: `"key": 12` where number was being written
  // (only if it's clearly truncated — skip if it looks complete)

  // Now close all open brackets
  const closers = computeClosers(s);
  if (closers === null) return null;

  return s + closers;
}

/**
 * Compute the closing characters needed to balance all open delimiters.
 */
function computeClosers(s: string): string | null {
  const stack: string[] = [];
  let inString = false;
  let escape = false;

  for (let i = 0; i < s.length; i++) {
    const ch = s[i];

    if (escape) {
      escape = false;
      continue;
    }

    if (ch === '\\' && inString) {
      escape = true;
      continue;
    }

    if (ch === '"') {
      inString = !inString;
      continue;
    }

    if (inString) continue;

    if (ch === '{') stack.push('}');
    else if (ch === '[') stack.push(']');
    else if (ch === '}' || ch === ']') {
      if (stack.length === 0) return null; // malformed
      const expected = stack.pop();
      if (expected !== ch) return null; // mismatched
    }
  }

  // If we're inside an unclosed string, close it first
  let prefix = '';
  if (inString) {
    prefix = '"';
  }

  return prefix + stack.reverse().join('');
}

/**
 * Progressively trim characters from the end until we find a valid close point.
 * This handles cases where truncation happened mid-value.
 */
function progressiveTrim(raw: string): string | null {
  let s = raw.trim();
  if (!s.startsWith('{') && !s.startsWith('[')) return null;

  // Try removing up to 200 chars from the end to find a clean cut point
  const maxTrim = Math.min(200, Math.floor(s.length * 0.1));

  for (let trim = 1; trim <= maxTrim; trim++) {
    let candidate = s.slice(0, s.length - trim);

    // Clean trailing artifacts
    candidate = candidate.replace(/,\s*$/, '');
    candidate = candidate.replace(/,?\s*"[^"]*"\s*:\s*$/, '');

    const closers = computeClosers(candidate);
    if (closers !== null) {
      try {
        const result = candidate + closers;
        JSON.parse(result); // validate
        return result;
      } catch {
        continue;
      }
    }
  }

  return null;
}

/**
 * Extract a partial object by finding completed top-level key-value pairs.
 * Scans for `"key": value,` patterns at the top level and builds
 * an object from the ones that parsed successfully.
 */
function extractPartialObject(raw: string): string | null {
  const s = raw.trim();
  if (!s.startsWith('{')) return null;

  // Find top-level key-value pairs by tracking brace/bracket depth
  const pairs: string[] = [];
  let i = 1; // skip opening {
  let depth = 0;
  let inStr = false;
  let esc = false;
  let pairStart = 1;

  while (i < s.length) {
    const ch = s[i];

    if (esc) { esc = false; i++; continue; }
    if (ch === '\\' && inStr) { esc = true; i++; continue; }
    if (ch === '"') { inStr = !inStr; i++; continue; }
    if (inStr) { i++; continue; }

    if (ch === '{' || ch === '[') depth++;
    else if (ch === '}' || ch === ']') {
      if (depth === 0) break; // closing of root object
      depth--;
    } else if (ch === ',' && depth === 0) {
      const pair = s.slice(pairStart, i).trim();
      if (pair) pairs.push(pair);
      pairStart = i + 1;
    }

    i++;
  }

  if (pairs.length === 0) return null;

  // Validate each pair individually
  const validPairs: string[] = [];
  for (const pair of pairs) {
    try {
      JSON.parse(`{${pair}}`);
      validPairs.push(pair);
    } catch {
      // skip this pair
    }
  }

  if (validPairs.length === 0) return null;

  return `{${validPairs.join(',')}}`;
}
