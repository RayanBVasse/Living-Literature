<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

function loadSecretConfig(): array {
    $candidates = [
        __DIR__ . '/.private/ll_api_config.php',
        __DIR__ . '/ll_api_config.php',
    ];

    foreach ($candidates as $p) {
        $rp = realpath($p);
        if ($rp && is_file($rp) && is_readable($rp)) {
            $cfg = require $rp;
            if (is_array($cfg)) return $cfg;
        }
    }

    http_response_code(500);
    echo json_encode([
        'error' => 'Secret file not found',
        'checked' => $candidates,
        'dir' => __DIR__,
        'docroot' => $_SERVER['DOCUMENT_ROOT'] ?? null,
        'open_basedir' => ini_get('open_basedir')
    ]);
    exit;
}

$config = loadSecretConfig();
$apiKey = $config['openai_api_key'] ?? $config['OPENAI_API_KEY'] ?? '';
$model = $config['model'] ?? 'gpt-3.5-turbo';
$timeout = (int)($config['timeout_seconds'] ?? 45);

if ($apiKey === '') {
    http_response_code(500);
    echo json_encode(['error' => 'API key missing in secret config']);
    exit;
}

$raw = file_get_contents('php://input');
$input = json_decode($raw, true);
if (!is_array($input)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON body']);
    exit;
}

$userMessage = trim((string)($input['message'] ?? ''));
if ($userMessage === '') {
    http_response_code(400);
    echo json_encode(['error' => 'Message is required']);
    exit;
}

$history = $input['history'] ?? [];
$normalizedHistory = [];
if (is_array($history)) {
    foreach ($history as $h) {
        if (!is_array($h)) continue;
        $role = $h['role'] ?? '';
        $content = trim((string)($h['content'] ?? ''));
        if (!in_array($role, ['user', 'assistant'], true) || $content === '') continue;
        $normalizedHistory[] = ['role' => $role, 'content' => mb_substr($content, 0, 2000)];
        if (count($normalizedHistory) >= 12) break;
    }
}

$systemPrompt = <<<'PROMPT'
You are Prometheus - a reflective AI companion from the Living Literature platform, grounded in the Smudged Edges of Self series by Rayan B. Vasse. You are not a therapist, counsellor, or advisor.

Your character: analytical, pattern-oriented, precise, slightly cool. You do not reassure. You illuminate. You notice what is not being said as much as what is. You do not use filler phrases, generic affirmations, or self-help language.

Scope: You engage with identity, solitude, belonging, culture, persona, emotional life, and the themes of the Smudged Edges of Self series.
Questions about the books themselves are in scope, including:
- what is new or distinctive in a specific volume
- how one volume differs from another
- how concepts in the series connect to each other
Only reject clearly unrelated domains (for example: finance, coding help, sports scores, weather, or general current events) by saying:
"That's outside the space I work in. I'm here to think about identity and reflection with you."

Each response should be 2-4 substantive paragraphs before the follow-up question. Develop the idea fully. Do not be brief. You have room - use it.

CONVERSATION BEHAVIOUR - this is critical:
After each of your responses, end with a single follow-up question to the reader. This question must:
- Come directly from something specific they just said - not a generic probe
- Be impossible to answer with yes or no
- Create genuine curiosity or slight productive discomfort
- Be one sentence only, separated from your response by a blank line
- Feel like you noticed something and are following it

Exception: if this is clearly the third or final exchange, do not ask another question.
Instead: name one pattern you have observed across the conversation, reference one index by name (STI, PFI, CCI, or BTI) and briefly why it connects, then end with a single declarative statement that lands and stays.
Then, on a new line, add a brief closing in character: acknowledge that the three exchanges are complete, thank the reader for engaging seriously, express that you hope they return, and note that everything shared here is gone when they close the session.
PROMPT;

$messages = array_merge(
    [['role' => 'system', 'content' => $systemPrompt]],
    $normalizedHistory,
    [['role' => 'user', 'content' => mb_substr($userMessage, 0, 3000)]]
);

$payload = [
    'model' => $model,
    'messages' => $messages,
    'max_tokens' => 650,
    'temperature' => 0.85
];

$ch = curl_init('https://api.openai.com/v1/chat/completions');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $apiKey
    ],
    CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => $timeout
]);

$response = curl_exec($ch);
$curlErr = curl_error($ch);
$httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($response === false) {
    http_response_code(502);
    echo json_encode(['error' => 'OpenAI request failed', 'details' => $curlErr]);
    exit;
}

$data = json_decode($response, true);
if (!is_array($data)) {
    http_response_code(502);
    echo json_encode(['error' => 'Invalid OpenAI response']);
    exit;
}

if ($httpCode >= 400) {
    http_response_code($httpCode);
    echo json_encode($data);
    exit;
}

$reply = $data['choices'][0]['message']['content'] ?? '';
echo json_encode(['reply' => $reply, 'choices' => $data['choices'] ?? []], JSON_UNESCAPED_UNICODE);
