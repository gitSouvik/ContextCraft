import React, { useState, useRef, useEffect } from 'react';
import { IconBase } from '../Icons';
import { sendChatQuestion } from '../../lib/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Props {
  jobId: string;
  isAvailable: boolean;
}

export const ChatTab: React.FC<Props> = ({ jobId, isAvailable }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading || !isAvailable) return;

    const userMsg = input.trim();
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setLoading(true);

    try {
      const res = await sendChatQuestion(jobId, userMsg);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.answer }]);
    } catch (err: any) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="box" style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', overflow: 'hidden' }}>
      <div className="box-header">
        <IconBase id="compass" /> Ask ContextCraft
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.length === 0 && (
          <div style={{ margin: 'auto', color: 'var(--text-faint)', textAlign: 'center' }}>
            {isAvailable 
              ? "Ask anything about this repository's codebase."
              : "Chat is still indexing..."}
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`} style={{ alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            {msg.content}
          </div>
        ))}
        {loading && <div className="chat-msg assistant" style={{ alignSelf: 'flex-start' }}>Thinking...</div>}
        <div ref={endRef} />
      </div>
      <div className="chat-input-row" style={{ borderTop: '1px solid var(--line)', background: 'var(--panel-2)' }}>
        <IconBase id="compass" />
        <input
          type="text"
          placeholder={isAvailable ? "Ask about this repo..." : "Chat is still indexing..."}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={!isAvailable || loading}
          style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--text)', fontSize: '13.5px' }}
        />
        <button className="chat-send" onClick={handleSend} disabled={!isAvailable || loading || !input.trim()}>
          <IconBase id="send" style={{ stroke: 'none', fill: 'currentColor' }} />
        </button>
      </div>
    </div>
  );
};
