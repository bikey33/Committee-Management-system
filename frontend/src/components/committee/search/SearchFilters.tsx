import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Filter, Check, ChevronsUpDown } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Committee } from "@/types/committee";
import { ComboboxFilter } from "@/components/common/ComboboxFilter";

import { User } from "@/types/auth";

interface SearchFiltersProps {
  searchTerm: string;
  setSearchTerm: (value: string) => void;
  formationDateFilter: string;
  setFormationDateFilter: (value: string) => void;
  statusFilter: string;
  setStatusFilter: (value: string) => void;
  typeFilter: string;
  setTypeFilter: (value: string) => void;
  officeFilter: string;
  setOfficeFilter: (value: string) => void;
  planFilter: string;
  setPlanFilter: (value: string) => void;
  committees: Committee[];
  user: User | null;
  canViewAllOffices?: boolean;
  filteredCount: number;
}


const SearchFilters = ({
  searchTerm,
  setSearchTerm,
  formationDateFilter,
  setFormationDateFilter,
  statusFilter,
  setStatusFilter,
  typeFilter,
  setTypeFilter,
  officeFilter,
  setOfficeFilter,
  planFilter,
  setPlanFilter,
  committees,
  user,
  canViewAllOffices = false,
  filteredCount,
}: SearchFiltersProps) => {
  
  // Extract unique offices and plans
  const officeOptions = useMemo(() => {
    let offices = Array.from(new Set(committees.map(c => {
      const code = c.office_code;
      const name = c.office_name;
      if (!code) return null;
      return name ? `${code}|${name}` : `${code}|${code}`;
    }).filter(Boolean)));
    
    let options = (offices as string[]).map(o => {
      const [code, name] = o.split('|');
      return { label: code === name ? code : `${code} - ${name}`, value: code };
    });

    // If not super admin or cross-office permission, only show user's office
    if (!canViewAllOffices && user?.office?.code) {
      options = options.filter(o => o.value === user.office?.code);
      // Ensure user's office is at least present if it's not in the committees list yet
      if (options.length === 0) {
        options = [{ 
          label: user.office.code === user.office.name ? user.office.code : `${user.office.code} - ${user.office.name}`, 
          value: user.office.code 
        }];
      }
    }

    return options;
  }, [committees, canViewAllOffices, user]);

  const planOptions = useMemo(() => {
    const plans = Array.from(new Set(committees.map(c => c.procurement_plan_name).filter(Boolean)));
    return plans.map(p => ({ label: p!, value: p! }));
  }, [committees]);

  return (
    <div className="pt-5 space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {/* Procurement Office Filter (Combobox) */}
        <div className="min-w-0">
          <ComboboxFilter
            value={officeFilter}
            onValueChange={setOfficeFilter}
            options={officeOptions}
            placeholder="Office"
            showAllOption={canViewAllOffices}
          />
        </div>

        {/* Procurement Plan Filter (Combobox) */}
        <div className="min-w-0">
          <ComboboxFilter
            value={planFilter}
            onValueChange={setPlanFilter}
            options={planOptions}
            placeholder="Procurement Plan"
          />
        </div>

        {/* Committee Type Filter */}
        <div className="min-w-0">
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="h-10 border-slate-200 bg-white shadow-sm font-medium text-slate-700 w-full">
              <div className="flex items-center gap-2">
                <Filter className="h-3.5 w-3.5 text-slate-400" />
                <SelectValue placeholder="Type" />
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="specification">Specification</SelectItem>
              <SelectItem value="evaluation">Evaluation</SelectItem>
              <SelectItem value="review">Review</SelectItem>
              <SelectItem value="contract">Contract Preparation</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Formation Date Filter - Improved width */}
        <div className="relative min-w-0">
          <label className="absolute -top-5 left-0 text-[10px] font-bold text-slate-500 tracking-wider">
            Formation Date
          </label>
          <Input
            type="date"
            value={formationDateFilter}
            onChange={(e) => setFormationDateFilter(e.target.value)} 
            className="h-10 text-sm border-slate-200 focus:border-primary focus:ring-primary/20 rounded-md w-full bg-white shadow-sm font-medium pr-1 px-2"
          />
        </div>

        {/* Status Filter */}
        <div className="min-w-0">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="h-10 border-slate-200 bg-white shadow-sm font-medium text-slate-700">
              <div className="flex items-center gap-2">
                <SelectValue placeholder="Status" />
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
};

export default SearchFilters;
