
import { Button } from "@/components/ui/button";
import { Package, TrendingUp } from "lucide-react";

interface ErrorStateProps {
  error: string;
}

const ErrorState = ({ error }: ErrorStateProps) => {
  return (
    <div className="flex justify-center items-center h-64 bg-gradient-to-br from-red-50 via-pink-50 to-rose-50 rounded-3xl border border-red-100/50 shadow-2xl backdrop-blur-sm">
      <div className="text-center">
        <div className="bg-gradient-to-r from-red-100 to-pink-100 rounded-2xl p-6 w-20 h-20 mx-auto mb-6 flex items-center justify-center shadow-lg">
          <Package className="h-10 w-10 text-red-600" />
        </div>
        <h3 className="text-xl font-bold text-gray-900 mb-3">Error loading committees</h3>
        <p className="text-sm text-gray-600 mb-6 max-w-sm mx-auto leading-relaxed">{error}</p>
        <Button
          variant="outline"
          className="bg-gradient-to-r from-red-50 to-pink-50 border-red-200 text-red-700 hover:from-red-100 hover:to-pink-100 shadow-lg hover:shadow-xl transition-all duration-300"
          onClick={() => window.location.reload()}
        >
          <TrendingUp className="h-4 w-4 mr-2" />
          Retry Loading
        </Button>
      </div>
    </div>
  );
};

export default ErrorState;
