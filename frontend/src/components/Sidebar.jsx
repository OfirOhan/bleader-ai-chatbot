import UserMenu from './UserMenu.jsx';
import Logo from './Logo.jsx';
import { useI18n } from '../i18n/index.jsx';

export default function Sidebar({
  conversations, activeId, onSelect, onNewChat, onDelete, user, onLogout,
}) {
  const { t } = useI18n();
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1><Logo size={22} className="sidebar-logo" /> AutoSage</h1>
        <button className="new-chat-btn" onClick={onNewChat}>
          <span>＋</span> {t('sidebar.newChat')}
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="sidebar-empty">
            {t('sidebar.emptyTitle')}<br />{t('sidebar.emptyHint')}
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${conv.id === activeId ? 'active' : ''}`}
              onClick={() => onSelect(conv.id)}
            >
              <div className="conversation-item-content">
                <div className="conversation-item-title">
                  {conv.title || t('sidebar.newConversation')}
                </div>
                {conv.last_message_preview && (
                  <div className="conversation-item-preview">
                    {conv.last_message_preview}
                  </div>
                )}
              </div>
              <button
                className="conversation-item-delete"
                onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
                title={t('sidebar.delete')}
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>

      {user && (
        <div className="sidebar-footer">
          <UserMenu user={user} onLogout={onLogout} />
        </div>
      )}
    </aside>
  );
}
