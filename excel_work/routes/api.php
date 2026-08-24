<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider and all of them will
| be assigned to the "api" middleware group. Make something great!
|
*/

use App\Http\Controllers\Api\TripController;
use App\Http\Controllers\Api\WaybillController;
use App\Http\Controllers\Api\SavedClientController;

Route::middleware('auth:sanctum')->get('/user', function (Request $request) {
    return $request->user();
});

Route::get('/saved-clients', [SavedClientController::class, 'index']);
Route::post('/saved-clients', [SavedClientController::class, 'store']);

Route::get('/trips', [TripController::class, 'index']);
Route::post('/trips', [TripController::class, 'store']);

Route::get('/waybills', [WaybillController::class, 'index']);
Route::post('/waybills', [WaybillController::class, 'store']);
Route::put('/waybills/{id}', [WaybillController::class, 'update']);
Route::delete('/waybills/truncate', [WaybillController::class, 'truncate']);
Route::delete('/waybills/{id}', [WaybillController::class, 'destroy']);
