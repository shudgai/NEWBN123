<?php
use App\Models\Waybill;

$waybills = Waybill::where('client_code', '639')->get();
$count = 0;

foreach ($waybills as $row) {
    // We only update if it's currently 0 or null
    // But wait, user said "之前沒輸入的堆高機填上"
    // So if forklift_fee is null or 0, we can calculate and update it.
    if (empty($row->forklift_fee)) {
        $weight = floatval($row->weight);
        $pieces = intval($row->pieces);
        $newFee = null;
        
        if ($weight >= 2000) {
            $newFee = null; // 另計
        } elseif ($weight >= 1000) {
            $newFee = 500;
        } elseif ($pieces >= 4) {
            $newFee = 500;
        } elseif ($weight >= 100) {
            $newFee = 250;
        }
        
        if ($newFee !== null && $newFee > 0) {
            $row->forklift_fee = $newFee;
            $row->save();
            $count++;
        }
    }
}
echo "Updated {$count} rows.\n";
