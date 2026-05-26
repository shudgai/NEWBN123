<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Price extends Model
{
    use HasFactory;

    protected $fillable = ['client_name', 'destination', 'price'];

    public function trips()
    {
        return $this->hasMany(Trip::class);
    }
}
