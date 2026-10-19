import React, { createContext, useContext, useEffect, useState } from 'react';

// Declare Telegram types on window
declare global {
  interface Window {
    Telegram?: {
      WebApp?: any;
    };
  }
}

interface TelegramContextType {
  isTelegram: boolean;
  webApp: any | null;
}

const mockWebApp = {
  ready: () => {},
  expand: () => {},
  close: () => {},
  sendData: (data: string) => {
    console.log("[Telegram Mock] sendData:", data);
  },
  initData: "user=%7B%22id%22%3A12345678%2C%22first_name%22%3A%22LocalDev%22%2C%22username%22%3A%22local_tester%22%7D",
  initDataUnsafe: {
    user: {
      id: 12345678,
      first_name: "LocalDev",
      username: "local_tester"
    }
  },
  themeParams: {
    bg_color: "#1e1e2e",
    text_color: "#cdd6f4",
    hint_color: "#a6adc8",
    link_color: "#89b4fa",
    button_color: "#89b4fa",
    button_text_color: "#11111b"
  },
  colorScheme: "dark"
};

const TelegramContext = createContext<TelegramContextType>({
  isTelegram: false,
  webApp: mockWebApp,
});

export const TelegramProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isTelegram, setIsTelegram] = useState(false);
  const [webApp, setWebApp] = useState<any>(mockWebApp);

  useEffect(() => {
    try {
      const realWebApp = typeof window !== 'undefined' ? (window as any).Telegram?.WebApp : null;
      if (realWebApp && realWebApp.initData) {
        if (typeof realWebApp.ready === 'function') realWebApp.ready();
        if (typeof realWebApp.expand === 'function') realWebApp.expand();
        setIsTelegram(true);
        setWebApp(realWebApp);
      } else {
        setIsTelegram(false);
        setWebApp(mockWebApp);
      }
    } catch {
      setIsTelegram(false);
      setWebApp(mockWebApp);
    }
  }, []);

  return (
    <TelegramContext.Provider value={{ isTelegram, webApp }}>
      {children}
    </TelegramContext.Provider>
  );
};

export const useTelegram = () => useContext(TelegramContext);
