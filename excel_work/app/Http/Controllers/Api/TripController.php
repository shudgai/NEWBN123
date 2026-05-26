<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Price;
use App\Models\Trip;
use Illuminate\Http\Request;

class TripController extends Controller
{
    public function index(Request $request)
    {
        $prices = Price::all();
        $date = $request->query('date', date('Y-m-d'));
        $trips = Trip::where('date', $date)->get();

        return response()->json([
            'prices' => $prices,
            'trips' => $trips,
            'date' => $date
        ]);
    }

    public function store(Request $request)
    {
        $request->validate([
            'date' => 'required|date',
            'trips' => 'required|array',
            'trips.*.price_id' => 'required|exists:prices,id',
            'trips.*.trips_count' => 'required|integer|min:0',
        ]);

        $date = $request->input('date');
        $tripsData = $request->input('trips');

        foreach ($tripsData as $trip) {
            Trip::updateOrCreate(
                ['date' => $date, 'price_id' => $trip['price_id']],
                ['trips_count' => $trip['trips_count']]
            );
        }

        return response()->json(['message' => 'Trips saved successfully']);
    }
}
