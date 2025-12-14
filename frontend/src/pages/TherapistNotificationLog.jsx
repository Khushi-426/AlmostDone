import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const TherapistNotificationLog = () => {
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const fetchLogs = async () => {
        try {
            const res = await axios.get('http://localhost:5001/api/therapist/notifications');
            setLogs(res.data);
        } catch(e) { console.error(e); }
    };
    fetchLogs();
  }, []);

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
       <button onClick={() => navigate('/therapist-dashboard')} className="mb-4 text-blue-600 underline">← Back</button>
      <h1 className="text-3xl font-bold mb-6">System Notifications</h1>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {logs.length === 0 ? <p className="p-6">No notifications yet.</p> : (
            <table className="min-w-full">
                <thead className="bg-gray-100">
                    <tr>
                        <th className="px-6 py-3 text-left">Time</th>
                        <th className="px-6 py-3 text-left">Type</th>
                        <th className="px-6 py-3 text-left">Message</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.map(log => (
                        <tr key={log.id} className="border-b">
                            <td className="px-6 py-4 text-sm text-gray-500">{log.date}</td>
                            <td className="px-6 py-4 text-sm font-bold text-blue-600">{log.type}</td>
                            <td className="px-6 py-4 text-sm text-gray-800">{log.message}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        )}
      </div>
    </div>
  );
};
export default TherapistNotificationLog;