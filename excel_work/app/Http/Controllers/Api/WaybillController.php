<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Waybill;
use Illuminate\Http\Request;

class WaybillController extends Controller
{
    public function index()
    {
        return response()->json(Waybill::orderBy('id', 'asc')->get());
    }

    public function store(Request $request)
    {
        $validated = $request->validate([
            'date' => 'required|string',
            'bill_no' => 'nullable|string',
            'client_name' => 'required|string',
            'amount' => 'required|numeric|min:0',
            'pieces' => 'required|numeric|min:0',
            'weight' => 'required|numeric|min:0',
            'location' => 'nullable|string',
            'remark' => 'nullable|string',
            'is_client_data' => 'nullable|boolean',
        ]);

        $waybill = Waybill::create($validated);

        return response()->json(['message' => 'Waybill saved successfully', 'data' => $waybill]);
    }

    public function update(Request $request, $id)
    {
        $waybill = Waybill::findOrFail($id);
        
        $validated = $request->validate([
            'date' => 'required|string',
            'bill_no' => 'nullable|string',
            'client_name' => 'required|string',
            'amount' => 'required|numeric|min:0',
            'pieces' => 'required|numeric|min:0',
            'weight' => 'required|numeric|min:0',
            'location' => 'nullable|string',
            'remark' => 'nullable|string',
            'is_client_data' => 'nullable|boolean',
        ]);

        $waybill->update($validated);

        return response()->json(['message' => 'Waybill updated successfully', 'data' => $waybill]);
    }

    public function destroy($id)
    {
        $waybill = Waybill::findOrFail($id);
        $waybill->delete();

        return response()->json(['message' => 'Waybill deleted successfully']);
    }

    public function truncate()
    {
        Waybill::truncate();
        return response()->json(['message' => 'All waybills truncated successfully']);
    }
}
