<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\SavedClient;
use Illuminate\Http\Request;

class SavedClientController extends Controller
{
    public function index(Request $request)
    {
        $clientCode = $request->query('client_code');
        if (!$clientCode) {
            return response()->json([]);
        }

        $clients = SavedClient::where('client_code', $clientCode)
            ->pluck('client_name')
            ->toArray();

        return response()->json($clients);
    }

    public function store(Request $request)
    {
        $validated = $request->validate([
            'client_code' => 'required|string',
            'client_name' => 'required|string',
        ]);

        SavedClient::firstOrCreate(
            ['client_code' => $validated['client_code'], 'client_name' => $validated['client_name']]
        );

        return response()->json(['message' => 'Saved successfully']);
    }
}
