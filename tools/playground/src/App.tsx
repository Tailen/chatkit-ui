import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Playground app for chatkit-ui development.
 *
 * Currently uses raw fetch + SSE parsing to talk to the dev server.
 * As chatkit-ui components are built, this should switch to:
 *
 *   import { ChatKit, useChatKit } from 'chatkit-ui';
 *   const { control } = useChatKit({ api: { url: '/chatkit' } });
 *   return <ChatKit control={control} />;
 */

const CHATKIT_URL = '/chatkit';

interface Message {
  role: 'user' | 'assistant';
  text: string;
  id?: string;
}

export function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      const userMsg: Message = { role: 'user', text: text.trim() };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setIsStreaming(true);

      const abortController = new AbortController();
      abortRef.current = abortController;

      // Build the request body
      const body = threadId
        ? {
            type: 'threads.runs.create',
            params: {
              thread_id: threadId,
              input: {
                content: [{ type: 'input_text', text: text.trim() }],
                attachments: [],
                inference_options: {},
              },
            },
          }
        : {
            type: 'threads.create',
            params: {
              input: {
                content: [{ type: 'input_text', text: text.trim() }],
                attachments: [],
                inference_options: {},
              },
            },
          };

      // Add a placeholder assistant message that we'll stream into
      const assistantIdx = messages.length + 1; // +1 for user message we just added
      setMessages((prev) => [...prev, { role: 'assistant', text: '' }]);

      try {
        const response = await fetch(CHATKIT_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          signal: abortController.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const jsonStr = line.slice(6);
            if (!jsonStr.trim()) continue;

            try {
              const event = JSON.parse(jsonStr);
              handleSSEEvent(event, assistantIdx);
            } catch {
              // Skip malformed JSON
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') {
          // User cancelled
        } else {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                text:
                  last.text +
                  `\n\n[Error: ${err instanceof Error ? err.message : String(err)}]`,
              };
            }
            return updated;
          });
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, threadId, messages.length],
  );

  const handleSSEEvent = (
    event: Record<string, unknown>,
    _assistantIdx: number,
  ) => {
    const type = event.type as string;

    switch (type) {
      case 'thread.created': {
        const thread = event.thread as { id: string };
        setThreadId(thread.id);
        break;
      }
      case 'thread.item.updated': {
        const update = event.update as Record<string, unknown> | undefined;
        if (update?.type === 'assistant_message.content_part.text_delta') {
          const text = update.delta as string;
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                text: last.text + text,
              };
            }
            return updated;
          });
        }
        break;
      }
      case 'error': {
        const error = event.error as { message?: string } | undefined;
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === 'assistant') {
            updated[updated.length - 1] = {
              ...last,
              text: `[Error: ${error?.message ?? 'Unknown error'}]`,
            };
          }
          return updated;
        });
        break;
      }
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
  };

  const handleNewThread = () => {
    setMessages([]);
    setThreadId(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>chatkit-ui playground</h1>
        <div style={styles.headerRight}>
          {threadId && (
            <span style={styles.threadId}>
              Thread: {threadId.slice(0, 8)}...
            </span>
          )}
          <button onClick={handleNewThread} style={styles.newThreadBtn}>
            New Thread
          </button>
        </div>
      </header>

      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.empty}>
            <p style={styles.emptyTitle}>chatkit-ui dev playground</p>
            <p style={styles.emptySubtitle}>
              Send a message to test the dev server. Try these keywords:
            </p>
            <div style={styles.chips}>
              {['hello', 'widget', 'error', 'long', 'slow', 'annotations'].map(
                (keyword) => (
                  <button
                    key={keyword}
                    style={styles.chip}
                    onClick={() => sendMessage(keyword)}
                  >
                    {keyword}
                  </button>
                ),
              )}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              ...styles.message,
              ...(msg.role === 'user'
                ? styles.userMessage
                : styles.assistantMessage),
            }}
          >
            <div style={styles.messageRole}>
              {msg.role === 'user' ? 'You' : 'Assistant'}
            </div>
            <div style={styles.messageText}>
              {msg.text ||
                (isStreaming && i === messages.length - 1 ? '...' : '')}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} style={styles.composer}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          style={styles.input}
          disabled={isStreaming}
        />
        {isStreaming ? (
          <button type="button" onClick={handleCancel} style={styles.cancelBtn}>
            Cancel
          </button>
        ) : (
          <button type="submit" disabled={!input.trim()} style={styles.sendBtn}>
            Send
          </button>
        )}
      </form>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    maxWidth: 720,
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    borderBottom: '1px solid #e5e5e5',
  },
  title: {
    fontSize: 16,
    fontWeight: 600,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  threadId: {
    fontSize: 12,
    color: '#666',
    fontFamily: 'monospace',
  },
  newThreadBtn: {
    fontSize: 13,
    padding: '4px 12px',
    borderRadius: 6,
    border: '1px solid #ccc',
    background: '#fff',
    cursor: 'pointer',
  },
  messages: {
    flex: 1,
    overflow: 'auto',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    gap: 8,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 600,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#666',
  },
  chips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 8,
  },
  chip: {
    fontSize: 13,
    padding: '6px 14px',
    borderRadius: 20,
    border: '1px solid #ddd',
    background: '#f9f9f9',
    cursor: 'pointer',
  },
  message: {
    padding: '10px 14px',
    borderRadius: 12,
    maxWidth: '85%',
  },
  userMessage: {
    alignSelf: 'flex-end',
    background: '#0d0d0d',
    color: '#fff',
  },
  assistantMessage: {
    alignSelf: 'flex-start',
    background: '#f0f0f0',
    color: '#0d0d0d',
  },
  messageRole: {
    fontSize: 11,
    fontWeight: 600,
    marginBottom: 4,
    opacity: 0.6,
  },
  messageText: {
    fontSize: 14,
    lineHeight: 1.5,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  composer: {
    display: 'flex',
    gap: 8,
    padding: '12px 16px',
    borderTop: '1px solid #e5e5e5',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    fontSize: 14,
    borderRadius: 8,
    border: '1px solid #ddd',
    outline: 'none',
  },
  sendBtn: {
    padding: '10px 20px',
    fontSize: 14,
    fontWeight: 500,
    borderRadius: 8,
    border: 'none',
    background: '#0d0d0d',
    color: '#fff',
    cursor: 'pointer',
  },
  cancelBtn: {
    padding: '10px 20px',
    fontSize: 14,
    fontWeight: 500,
    borderRadius: 8,
    border: '1px solid #d00',
    background: '#fff',
    color: '#d00',
    cursor: 'pointer',
  },
};
