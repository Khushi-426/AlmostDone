import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const TherapistExerciseLibrary = () => {
  const navigate = useNavigate();
  const [exercises, setExercises] = useState([]);
  const [newExercise, setNewExercise] = useState({ name: '', category: 'Mobility', difficulty: 'Beginner' });
  const [loading, setLoading] = useState(true);

  // Fetch Exercises from DB
  useEffect(() => {
    fetchExercises();
  }, []);

  const fetchExercises = async () => {
    try {
      const res = await axios.get('http://localhost:5001/api/therapist/exercises');
      setExercises(res.data);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const handleAddExercise = async (e) => {
    e.preventDefault();
    try {
      await axios.post('http://localhost:5001/api/therapist/exercises', newExercise);
      fetchExercises(); // Refresh list
      setNewExercise({ name: '', category: 'Mobility', difficulty: 'Beginner' });
      alert("Exercise Saved to DB!");
    } catch (err) {
      alert("Error saving exercise");
    }
  };

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <button onClick={() => navigate('/therapist-dashboard')} className="mb-4 text-blue-600 underline">← Back</button>
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Exercise Library</h1>
      
      {/* Add Exercise Form */}
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <h3 className="text-xl font-bold mb-4">Add New Exercise</h3>
        <form onSubmit={handleAddExercise} className="flex gap-4">
          <input 
            className="border p-2 rounded flex-1" 
            placeholder="Exercise Name (e.g. Squat)" 
            value={newExercise.name}
            onChange={(e) => setNewExercise({...newExercise, name: e.target.value})}
            required
          />
          <select 
            className="border p-2 rounded"
            value={newExercise.category}
            onChange={(e) => setNewExercise({...newExercise, category: e.target.value})}
          >
            <option>Mobility</option><option>Strength</option><option>Balance</option>
          </select>
          <select 
            className="border p-2 rounded"
            value={newExercise.difficulty}
            onChange={(e) => setNewExercise({...newExercise, difficulty: e.target.value})}
          >
            <option>Beginner</option><option>Intermediate</option><option>Advanced</option>
          </select>
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">Add to DB</button>
        </form>
      </div>

      {/* List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {exercises.map(ex => (
          <div key={ex.id} className="bg-white p-6 rounded-lg shadow border-l-4 border-blue-500">
            <h3 className="font-bold text-xl">{ex.name}</h3>
            <p className="text-gray-600">Category: {ex.category}</p>
            <p className="text-gray-600">Difficulty: {ex.difficulty}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
export default TherapistExerciseLibrary;