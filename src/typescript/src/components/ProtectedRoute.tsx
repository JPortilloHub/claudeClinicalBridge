import { Navigate } from 'react-router-dom';
import { isAuthenticated } from '../api/auth';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
