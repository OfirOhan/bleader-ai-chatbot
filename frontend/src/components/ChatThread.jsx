import { useEffect, useRef } from 'react';
import AnswerCard from './AnswerCard.jsx';
import { useI18n } from '../i18n/index.jsx';

export default function ChatThread({ messages, thinking }) {
  const { t } = useI18n();
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  if (messages.length === 0) return null;

  return (
    <div className="chat-thread">
      <div className="messages-container">
        {messages.map((msg) => (
          <div key={msg.id} className={`message message-${msg.role}`}>
            <div className="message-label">
              {msg.role === 'user' ? t('you') : t('assistant.name')}
            </div>
            {msg.role === 'user' ? (
              <div className="message-bubble">{msg.content}</div>
            ) : (
              <AnswerCard message={msg} />
            )}
          </div>
        ))}

        {thinking && (
          <div className="message message-assistant">
            <div className="message-label">{t('assistant.name')}</div>
            <div className="typing"><span /><span /><span /></div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
