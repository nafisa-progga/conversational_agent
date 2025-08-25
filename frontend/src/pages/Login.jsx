import React, { useState } from 'react';
import { LogIn } from 'lucide-react';

const LoginPage = ({ setPage, setUser }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      const response = await fetch('http://127.0.0.1:8000/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed.');
      }

      const { token } = await response.json();
      const auth = import.meta.env.FIREBASE_AUTH; // Assuming auth is available via import.meta.env
      await auth.signInWithCustomToken(token);
      setPage('chat');
    } catch (err) {
      setError(err.message);
      console.error('Login error:', err);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full p-6 bg-gray-50 rounded-lg shadow-inner">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Login</h1>
      <form onSubmit={handleLogin} className="w-full max-w-sm">
        {error && <p className="text-red-500 text-sm text-center mb-4">{error}</p>}
        <div className="mb-4">
          <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="shadow appearance-none border rounded-full w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            required
          />
        </div>
        <div className="mb-6">
          <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="shadow appearance-none border rounded-full w-full py-3 px-4 text-gray-700 mb-3 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            required
          />
        </div>
        <div className="flex items-center justify-between">
          <button
            type="submit"
            className="flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white font-semibold rounded-full shadow-md hover:bg-blue-700 transition duration-300 w-full justify-center"
          >
            <LogIn size={20} />
            <span>Login</span>
          </button>
        </div>
      </form>
      <button
        onClick={() => setPage('signup')}
        className="mt-4 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        Don't have an account? Sign Up
      </button>
    </div>
  );
};

export default LoginPage;
