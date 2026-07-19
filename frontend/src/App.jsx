import { useState, useEffect } from 'react';
import AuthPage from './components/AuthPage.jsx';
import Sidebar from './components/Sidebar.jsx';
import ChatThread from './components/ChatThread.jsx';
import MessageInput from './components/MessageInput.jsx';
import PreferencesBar from './components/PreferencesBar.jsx';
import Logo from './components/Logo.jsx';
import { useI18n } from './i18n/index.jsx';
import * as api from './api.js';

export default function App() {
  const { t, lang } = useI18n();
  const [user, setUser] = useState(api.getUser());
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [preferences, setPreferences] = useState(null);
  const [sending, setSending] = useState(false);

  // Load conversations on sign-in.
  useEffect(() => {
    if (user) api.listConversations().then(setConversations).catch(console.error);
  }, [user]);

  // Load messages when the active conversation changes.
  useEffect(() => {
    if (activeConvId) {
      api.getMessages(activeConvId).then(setMessages).catch(console.error);
      const conv = conversations.find((c) => c.id === activeConvId);
      setPreferences(conv?.preferences || null);
    } else {
      setMessages([]);
      setPreferences(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConvId]);

  const handleAuthSuccess = (userData) => {
    setUser(userData);
    setConversations([]);
    setActiveConvId(null);
    setMessages([]);
  };

  const handleLogout = () => {
    api.logout();
    setUser(null);
    setConversations([]);
    setActiveConvId(null);
    setMessages([]);
    setPreferences(null);
  };

  const handleNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
    setPreferences(null);
  };

  const handleSelectConv = async (convId) => {
    setActiveConvId(convId);
  };

  const handleDeleteChat = async (convId) => {
    if (!window.confirm(t('confirm.deleteConversation'))) return;
    try {
      await api.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConvId === convId) handleNewChat();
    } catch (e) {
      console.error('Failed to delete conversation:', e);
    }
  };

  const handleSend = async (content) => {
    if (!content.trim() || sending) return;

    let convId = activeConvId;
    if (!convId) {
      try {
        const conv = await api.createConversation();
        setConversations((prev) => [conv, ...prev]);
        convId = conv.id;
        setActiveConvId(convId);
      } catch (e) {
        console.error('Failed to create conversation:', e);
        return;
      }
    }

    // Optimistically show the user's message + a typing indicator.
    const optimistic = { id: `tmp-${Date.now()}`, role: 'user', content };
    setMessages((prev) => [...prev, optimistic]);
    setSending(true);
    try {
      const result = await api.sendMessage(convId, content, lang);
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimistic.id),
        result.user_message,
        result.assistant_message,
      ]);
      if (result.preferences) setPreferences(result.preferences);
      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? { ...c, title: c.title || result.conversation_title || content.slice(0, 60),
                last_message_preview: content, preferences: result.preferences }
            : c
        )
      );
    } catch (e) {
      console.error('Failed to send message:', e);
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  };

  if (!user) return <AuthPage onAuthSuccess={handleAuthSuccess} />;

  return (
    <div className="app-layout">
      <Sidebar
        conversations={conversations}
        activeId={activeConvId}
        onSelect={handleSelectConv}
        onNewChat={handleNewChat}
        onDelete={handleDeleteChat}
        user={user}
        onLogout={handleLogout}
      />
      <div className="chat-area">
        {messages.length === 0 && !sending ? (
          <div className="chat-hero">
            <Logo size={52} className="chat-hero-logo" />
            <h1>{t('hero.title')}</h1>
            <p>{t('hero.subtitle')}</p>
            <MessageInput onSend={handleSend} disabled={sending} autoFocus />
          </div>
        ) : (
          <>
            <PreferencesBar preferences={preferences} />
            <ChatThread messages={messages} thinking={sending} />
            <MessageInput onSend={handleSend} disabled={sending} />
          </>
        )}
      </div>
    </div>
  );
}
