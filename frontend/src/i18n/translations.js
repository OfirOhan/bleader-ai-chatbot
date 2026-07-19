/**
 * UI translations. The content the bot reasons over is Hebrew, so the interface
 * ships bilingual (English + Hebrew, RTL-aware). Add a language by adding an
 * entry to LANGUAGES and a matching MESSAGES block; missing keys fall back to
 * English automatically.
 */

export const DEFAULT_LANG = 'en';

export const LANGUAGES = {
  en: { label: 'English', dir: 'ltr' },
  he: { label: 'עברית', dir: 'rtl' },
};

export const MESSAGES = {
  en: {
    'auth.subtitle': 'Grounded car advice from real road tests',
    'auth.email': 'Email',
    'auth.emailHint': "We'll create your account if it's your first time. No password needed.",
    'auth.continueEmail': 'Continue with email',
    'auth.pleaseWait': 'Please wait…',

    'sidebar.newChat': 'New chat',
    'sidebar.emptyTitle': 'No conversations yet.',
    'sidebar.emptyHint': 'Ask about a car to get started!',
    'sidebar.newConversation': 'New conversation',
    'sidebar.delete': 'Delete conversation',

    'input.placeholder': 'Ask about a car… e.g. "Is the Citroën C3 good value?"',
    'input.send': 'Send',

    'hero.title': 'Which car is right for you?',
    'hero.subtitle': 'Ask and compare across 8 professional road tests — every answer is grounded in the reviews and cites its sources.',

    'answer.sources': 'Sources',
    'pref.label': 'What I know so far',

    'menu.language': 'Language',
    'menu.theme': 'Theme',
    'menu.lightMode': 'Light',
    'menu.darkMode': 'Dark',
    'menu.logout': 'Log out',

    'lang.title': 'Language',
    'lang.subtitle': 'Choose the language for the interface.',
    'common.dismiss': 'Dismiss',
    'common.close': 'Close',
    'confirm.deleteConversation': 'Delete this conversation?',
    'assistant.name': 'AutoSage',
    'you': 'You',
  },

  he: {
    'auth.subtitle': 'ייעוץ רכב מבוסס על מבחני דרכים אמיתיים',
    'auth.email': 'אימייל',
    'auth.emailHint': 'ניצור לך חשבון בכניסה הראשונה. אין צורך בסיסמה.',
    'auth.continueEmail': 'המשך עם אימייל',
    'auth.pleaseWait': 'רגע…',

    'sidebar.newChat': "שיחה חדשה",
    'sidebar.emptyTitle': 'אין עדיין שיחות.',
    'sidebar.emptyHint': 'שאלו על רכב כדי להתחיל!',
    'sidebar.newConversation': 'שיחה חדשה',
    'sidebar.delete': 'מחיקת שיחה',

    'input.placeholder': 'שאלו על רכב… למשל "האם הסיטרואן C3 שווה את המחיר?"',
    'input.send': 'שליחה',

    'hero.title': 'איזה רכב מתאים לך?',
    'hero.subtitle': 'שאלו והשוו בין 8 מבחני דרכים מקצועיים — כל תשובה מבוססת על המבחנים ומצטטת את המקורות.',

    'answer.sources': 'מקורות',
    'pref.label': 'מה שידוע לי עד כה',

    'menu.language': 'שפה',
    'menu.theme': 'ערכת נושא',
    'menu.lightMode': 'בהיר',
    'menu.darkMode': 'כהה',
    'menu.logout': 'התנתקות',

    'lang.title': 'שפה',
    'lang.subtitle': 'בחרו את שפת הממשק.',
    'common.dismiss': 'סגירה',
    'common.close': 'סגירה',
    'confirm.deleteConversation': 'למחוק את השיחה?',
    'assistant.name': 'AutoSage',
    'you': 'אתה',
  },
};
