import React, { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInWithCustomToken, onAuthStateChanged } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

// Pages
import HomePage from './pages/Home.jsx';
import LoginPage from './pages/Login.jsx';
import SignupPage from './pages/Signup.jsx';
import ChatPage from './pages/Chat.jsx';

// Firebase configuration. This is automatically provided by the Canvas environment.
const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : {};

// Initialize Firebase App
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

const App = () => {
  const [page, setPage] = useState('home');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Auth state listener to handle user changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      setLoading(false);
      // Route to chat page if authenticated
      if (currentUser) {
        setPage('chat');
      }
    });

    return () => unsubscribe();
  }, []);

  // Simple state-based router
  const renderPage = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-full">
          <svg className="animate-spin h-8 w-8 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      );
    }

    switch (page) {
      case 'home':
        return <HomePage setPage={setPage} />;
      case 'login':
        return <LoginPage setPage={setPage} setUser={setUser} />;
      case 'signup':
        return <SignupPage setPage={setPage} setUser={setUser} />;
      case 'chat':
        return <ChatPage user={user} setPage={setPage} db={db} auth={auth} />;
      default:
        return <HomePage setPage={setPage} />;
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4 font-sans antialiased">
      <div className="w-full max-w-4xl h-[80vh] bg-white rounded-2xl shadow-xl flex flex-col overflow-hidden">
        {renderPage()}
      </div>
    </div>
  );
};

export default App;
