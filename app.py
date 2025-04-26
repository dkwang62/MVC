import React, { useState, useEffect } from 'react';
import { format, eachDayOfInterval, endOfMonth } from 'date-fns';
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogTrigger, DialogContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import fullData from "../../public/projected_ko_olina_2025_2027.json";

export default function MonthlyPointsViewer() {
  const [resortList, setResortList] = useState(Object.keys(fullData));
  const [resort, setResort] = useState(resortList[0]);
  const [unitList, setUnitList] = useState(Object.keys(fullData[resort]));
  const [unit, setUnit] = useState(unitList[0]);
  const [viewList, setViewList] = useState(Object.keys(fullData[resort][unit]));
  const [view, setView] = useState(viewList[0]);
  const [year, setYear] = useState("2025");
  const [month, setMonth] = useState("01");
  const [selectedDate, setSelectedDate] = useState(null);
  const [newPoints, setNewPoints] = useState("");
  const [_, forceUpdate] = useState(0);

  useEffect(() => {
    setUnitList(Object.keys(fullData[resort]));
  }, [resort]);

  useEffect(() => {
    setUnit(unitList[0]);
  }, [unitList]);

  useEffect(() => {
    if (resort && unit) {
      setViewList(Object.keys(fullData[resort][unit]));
    }
  }, [resort, unit]);

  useEffect(() => {
    setView(viewList[0]);
  }, [viewList]);

  const start = new Date(`${year}-${month}-01`);
  const end = endOfMonth(start);
  const days = eachDayOfInterval({ start, end });

  const getPoints = (date) => {
    const formatted = format(date, 'yyyy-MM-dd');
    return fullData[resort]?.[unit]?.[view]?.[formatted] ?? '—';
  };

  const updatePoints = () => {
    if (!selectedDate || isNaN(parseInt(newPoints))) return;
    const formatted = format(selectedDate, 'yyyy-MM-dd');
    fullData[resort][unit][view][formatted] = parseInt(newPoints);
    setNewPoints("");
    setSelectedDate(null);
    forceUpdate(n => n + 1);
  };

  const saveToFile = () => {
    const element = document.createElement("a");
    const file = new Blob([JSON.stringify(fullData, null, 2)], { type: 'application/json' });
    element.href = URL.createObjectURL(file);
    element.download = "mvc_full_projected_2025_2027_updated.json";
    document.body.appendChild(element);
    element.click();
  };

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-5 gap-4">
        <Select value={resort} onValueChange={setResort}>
          <SelectTrigger><SelectValue placeholder="Resort" /></SelectTrigger>
          <SelectContent>{resortList.map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={unit} onValueChange={setUnit}>
          <SelectTrigger><SelectValue placeholder="Unit Type" /></SelectTrigger>
          <SelectContent>{unitList.map(u => <SelectItem key={u} value={u}>{u}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={view} onValueChange={setView}>
          <SelectTrigger><SelectValue placeholder="View Type" /></SelectTrigger>
          <SelectContent>{viewList.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={year} onValueChange={setYear}>
          <SelectTrigger><SelectValue placeholder="Year" /></SelectTrigger>
          <SelectContent>{["2025", "2026", "2027"].map(y => <SelectItem key={y} value={y}>{y}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={month} onValueChange={setMonth}>
          <SelectTrigger><SelectValue placeholder="Month" /></SelectTrigger>
          <SelectContent>{[
            { label: "January", value: "01" }, { label: "February", value: "02" },
            { label: "March", value: "03" }, { label: "April", value: "04" },
            { label: "May", value: "05" }, { label: "June", value: "06" },
            { label: "July", value: "07" }, { label: "August", value: "08" },
            { label: "September", value: "09" }, { label: "October", value: "10" },
            { label: "November", value: "11" }, { label: "December", value: "12" }
          ].map(m => <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="text-right">
        <Button onClick={saveToFile}>Save Changes to File</Button>
      </div>

      <div className="grid grid-cols-7 gap-2">
        {days.map((day, idx) => (
          <Dialog key={idx}>
            <DialogTrigger asChild>
              <Card onClick={() => setSelectedDate(day)} className="text-center cursor-pointer hover:bg-gray-100">
                <CardContent>
                  <div className="font-semibold">{format(day, 'dd MMM')}</div>
                  <div>{getPoints(day)} pts</div>
                </CardContent>
              </Card>
            </DialogTrigger>
            <DialogContent>
              <h2 className="text-lg font-bold">Update Points for {format(day, 'yyyy-MM-dd')}</h2>
              <Input type="number" value={newPoints} onChange={(e) => setNewPoints(e.target.value)} placeholder="Enter new points" />
              <Button onClick={updatePoints}>Update</Button>
            </DialogContent>
          </Dialog>
        ))}
      </div>
    </div>
  );
}
