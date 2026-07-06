<?php

use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Here is where you can register web routes for your application. These
| routes are loaded by the RouteServiceProvider and all of them will
| be assigned to the "web" middleware group. Make something great!
|
*/

Route::get('/', function () {
    return view('welcome');
});

Route::get('/client/206', function () {
    return view('client_206');
});

Route::get('/client/225', function () {
    return view('client_225');
});

Route::get('/client/276', function () {
    return view('client_276');
});

Route::get('/client/282', function () {
    return view('client_282');
});

Route::get('/client/444', function () {
    return view('client_444');
});

Route::get('/client/639', function () {
    return view('client_639');
});

Route::get('/merge-excel', [\App\Http\Controllers\MergeExcelController::class, 'index']);
Route::post('/merge-excel', [\App\Http\Controllers\MergeExcelController::class, 'merge']);
Route::post('/upload-temp', [\App\Http\Controllers\MergeExcelController::class, 'uploadTemp']);

Auth::routes();

Route::get('/home', [App\Http\Controllers\HomeController::class, 'index'])->name('home');
