import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TherapistDashboard = () => {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      // Ensure the port matches your Flask app (5001 based on your app.py)
      const response = await axios.get('http://localhost:5001/api/therapist/patients');
      setPatients(response.data.patients);
      setLoading(false);
    } catch (err) {
      console.error("Error fetching data:", err);
      setError("Failed to load patient data.");
      setLoading(false);
    }
  };

  if (loading) return <div className="p-10 text-center">Loading real patient data...</div>;
  if (error) return <div className="p-10 text-center text-red-500">{error}</div>;

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Therapist Dashboard</h1>
      
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full leading-normal">
            <thead>
              <tr className="bg-blue-600 text-white">
                <th className="px-5 py-3 text-left text-sm font-semibold uppercase tracking-wider">Patient Name</th>
                <th className="px-5 py-3 text-left text-sm font-semibold uppercase tracking-wider">Email</th>
                <th className="px-5 py-3 text-left text-sm font-semibold uppercase tracking-wider">Joined Date</th>
                <th className="px-5 py-3 text-left text-sm font-semibold uppercase tracking-wider">Status</th>
                <th className="px-5 py-3 text-left text-sm font-semibold uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {patients.length > 0 ? (
                patients.map((patient) => (
                  <tr key={patient.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 w-10 h-10">
                          <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold">
                            {patient.name.charAt(0).toUpperCase()}
                          </div>
                        </div>
                        <div className="ml-3">
                          <p className="text-gray-900 font-medium">{patient.name}</p>
                          <p className="text-gray-500 text-xs">ID: {patient.id.slice(-4)}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-gray-700">
                      {patient.email}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-gray-700">
                      {patient.date_joined}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        Active
                      </span>
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-sm font-medium">
                      <button className="text-blue-600 hover:text-blue-900 mr-4">
                        View History
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="px-5 py-10 text-center text-gray-500">
                    No patients found in the database.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default TherapistDashboard;