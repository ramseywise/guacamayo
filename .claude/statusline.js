// Claude Code Status Line - reads JSON from stdin, outputs formatted status
const chunks = [];
process.stdin.on('data', chunk => chunks.push(chunk));
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(Buffer.concat(chunks).toString());

    // Extract values
    const model = data.model?.display_name || 'Claude';
    const usage = data.context_window?.current_usage;
    const windowSize = data.context_window?.context_window_size || 200000;

    // Calculate context percentage
    let contextPct = 0;
    if (usage) {
      const totalTokens = (usage.input_tokens || 0) +
                          (usage.cache_creation_input_tokens || 0) +
                          (usage.cache_read_input_tokens || 0);
      contextPct = Math.round((totalTokens / windowSize) * 100);
    }

    // Color context based on usage (ANSI: 92=green, 93=yellow, 91=red)
    let pctColor = '\x1b[92m'; // green
    if (contextPct > 50) pctColor = '\x1b[93m'; // yellow
    if (contextPct > 75) pctColor = '\x1b[91m'; // red
    const reset = '\x1b[0m';

    // Output: Context% | Model
    console.log(`${pctColor}${contextPct}%${reset} | ${model}`);
  } catch (e) {
    console.log('--');
  }
});
