import React, { useState, useEffect } from 'react';
import { MessageSquare, LogOut, Loader } from 'lucide-react';
import { 
  collection, 
  onSnapshot,
  query,
  addDoc,
  serverTimestamp,
  orderBy
} from 'firebase/firestore';

const ChatPage = ({ user, setPage, db, auth }) => {
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);

  // Fetch messages from Firestore for chat history
  useEffect(() => {
    if (user) {
      const q = query(
        collection(db, `artifacts/${__app_id}/users/${user.uid}/messages`),
        orderBy('timestamp')
      );
      const unsubscribe = onSnapshot(q, (snapshot) => {
        const fetchedMessages = snapshot.docs.map(doc => doc.data());
        setMessages(fetchedMessages);
      }, (error) => {
        console.error("Error fetching messages:", error);
      });

      return () => unsubscribe();
    }
  }, [user]);

  const handleSendMessage = async () => {
    if (chatInput.trim() === '' || isSending) return;
    setIsSending(true);

    const userMessage = { text: chatInput, sender: 'user', timestamp: Date.now() };
    setMessages(prevMessages => [...prevMessages, userMessage]);

    try {
      await addDoc(collection(db, `artifacts/${__app_id}/users/${user.uid}/messages`), {
        text: chatInput,
        sender: 'user',
        timestamp: serverTimestamp()
      });

      const idToken = await user.getIdToken();
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`
        },
        body: JSON.stringify({ query: chatInput }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      await addDoc(collection(db, `artifacts/${__app_id}/users/${user.uid}/messages`), {
        text: data.response,
        sender: 'ai',
        timestamp: serverTimestamp()
      });
      
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage = { text: 'Sorry, something went wrong. Please try again.', sender: 'ai', timestamp: Date.now() };
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setIsSending(false);
      setChatInput('');
    }
  };

  const handleLogout = async () => {
    await auth.signOut();
    setMessages([]);
    setPage('home');
  };

  return (
    <div className="flex flex-col h-full w-full bg-gray-50 rounded-lg shadow-inner">
      <header className="flex items-center justify-between p-4 bg-gray-100 border-b border-gray-200 rounded-t-lg">
        <h2 className="text-xl font-bold text-gray-800">
          <MessageSquare className="inline-block mr-2 text-blue-600" />
          Conversational Agent
        </h2>
        <button
          onClick={handleLogout}
          className="flex items-center space-x-1 px-4 py-2 bg-red-500 text-white text-sm font-semibold rounded-full shadow-md hover:bg-red-600 transition duration-300"
        >
          <LogOut size={16} />
          <span>Logout</span>
        </button>
      </header>
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs md:max-w-md lg:max-w-lg p-3 rounded-xl shadow-sm ${
                msg.sender === 'user'
                  ? 'bg-blue-500 text-white rounded-br-none'
                  : 'bg-gray-200 text-gray-800 rounded-bl-none'
              }`}
            >
              <p>{msg.text}</p>
            </div>
          </div>
        ))}
        {isSending && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-800 p-3 rounded-xl rounded-bl-none shadow-sm">
              <Loader className="animate-spin" size={20} />
            </div>
          </div>
        )}
      </div>
      <footer className="p-4 bg-gray-100 border-t border-gray-200 rounded-b-lg">
        <div className="flex space-x-3">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSendMessage();
            }}
            placeholder="Ask the agent a question..."
            className="flex-1 p-3 border border-gray-300 rounded-full shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
          />
          <button
            onClick={handleSendMessage}
            disabled={isSending}
            className={`px-6 py-3 font-semibold rounded-full shadow-sm transition-colors duration-300 ${
              isSending
                ? 'bg-blue-300 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            Send
          </button>
        </div>
      </footer>
    </div>
  );
};

export default ChatPage;
