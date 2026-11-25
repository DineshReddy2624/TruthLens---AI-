import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import VerifyClaim from './pages/VerifyClaim';
import VerifyArticle from './pages/VerifyArticle';
import VerifyFile from './pages/VerifyFile';
import VerifyUrl from './pages/VerifyUrl';
import VerificationDetail from './pages/VerificationDetail';
import History from './pages/History';
import Admin from './pages/Admin';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Protected application routes */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/verify/claim" element={<VerifyClaim />} />
        <Route path="/verify/article" element={<VerifyArticle />} />
        <Route path="/verify/file" element={<VerifyFile />} />
        <Route path="/verify/url" element={<VerifyUrl />} />
        <Route path="/requests/:id" element={<VerificationDetail />} />
        <Route path="/history" element={<History />} />
        <Route path="/admin" element={<Admin />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
