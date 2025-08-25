import React from 'react';
import { LogIn, UserPlus } from 'lucide-react';

const HomePage = ({ setPage }) => (
  <div className="flex flex-col items-center justify-center h-full text-center p-6 bg-gray-50 rounded-lg shadow-inner">
    <h1 className="text-3xl font-bold text-gray-800 mb-4">Welcome to the Conversational Agent</h1>
    <p className="text-gray-600 mb-8">
      This agent uses a multi-tool LangGraph framework with memory to handle your queries.
    </p>
    <div className="flex space-x-4">
      <button
        onClick={() => setPage('login')}
        className="flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white font-semibold rounded-full shadow-md hover:bg-blue-700 transition duration-300"
      >
        <LogIn size={20} />
        <span>Login</span>
      </button>
      <button
        onClick={() => setPage('signup')}
        className="flex items-center space-x-2 px-6 py-3 bg-green-600 text-white font-semibold rounded-full shadow-md hover:bg-green-700 transition duration-300"
      >
        <UserPlus size={20} />
        <span>Sign Up</span>
      </button>
    </div>
  </div>
);

export default HomePage;
