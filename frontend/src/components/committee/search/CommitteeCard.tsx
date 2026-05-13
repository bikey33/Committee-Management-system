import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users, Calendar, Package, MapPin, Clock, FileText, Eye, CheckSquare, ScrollText } from "lucide-react";
import { Committee } from "@/types/committee";
import { useAuth } from "@/contexts/AuthContext";

interface CommitteeCardProps {
  committee: Committee;
  index: number;
  onClick?: () => void;
}

const CommitteeCard = ({ committee, index, onClick }: CommitteeCardProps) => {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();

  const handleCardClick = () => {
    if (onClick) {
      onClick();
    } else {
      // Fallback to navigation
      if (committee._id && committee._id !== "undefined" && committee._id !== "null") {
        navigate(`/committees/${committee._id}`);
      }
    }
  };

  const getCommitteeTypeIcon = (type: string) => {
    switch (type) {
      case "specification":
        return <FileText className="h-5 w-5 text-white" />;
      case "review":
        return <Eye className="h-5 w-5 text-white" />;
      case "evaluation":
        return <CheckSquare className="h-5 w-5 text-white" />;
      case "contract":
        return <ScrollText className="h-5 w-5 text-white" />;
      default:
        return <Users className="h-5 w-5 text-white" />;
    }
  };

  const getCommitteeTypeColor = (type: string) => {
    switch (type) {
      case "specification":
        return "from-blue-500 to-indigo-600";
      case "review":
        return "from-purple-500 to-pink-600";
      case "evaluation":
        return "from-green-500 to-emerald-600";
      case "contract":
        return "from-amber-500 to-orange-600";
      default:
        return "from-gray-500 to-slate-600";
    }
  };

  const getCommitteeTypeBadgeColor = (type: string) => {
    switch (type) {
      case "specification":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "review":
        return "bg-purple-100 text-purple-800 border-purple-200";
      case "evaluation":
        return "bg-green-100 text-green-800 border-green-200";
      case "contract":
        return "bg-amber-100 text-amber-800 border-amber-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  return (
    <Card
      key={typeof committee._id === 'object' ? JSON.stringify(committee._id) : String(committee._id)}
      className="group relative bg-gradient-to-br from-white/95 via-gray-50/90 to-blue-50/80 backdrop-blur-xl border-0 shadow-2xl hover:shadow-3xl transition-all duration-700 transform hover:scale-[1.01] cursor-pointer overflow-hidden animate-slideIn"
      style={{ animationDelay: `${index * 150}ms` }}
    >
      {/* Premium Gradient Top Border */}
      <div className="h-2 bg-gradient-to-r from-blue-500 via-indigo-500 via-purple-500 to-pink-500 relative">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 via-indigo-600 via-purple-600 to-pink-600 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
      </div>

      {/* Floating Background Elements */}
      <div className="absolute top-4 right-4 w-32 h-32 bg-gradient-to-br from-blue-400/5 to-purple-500/5 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
      <div
        className="absolute bottom-4 left-4 w-24 h-24 bg-gradient-to-tr from-indigo-400/5 to-pink-500/5 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700"
        style={{ transitionDelay: "200ms" }}
      ></div>

      <div className="relative p-8">
        <div className="flex flex-col gap-6">
          {/* Enhanced Header Section */}
          <div className="flex items-start justify-between">
            <div className="flex-1 cursor-pointer group/header" onClick={handleCardClick}>
              <div className="flex items-center gap-3 mb-3">
                <div
                  className={`p-2 bg-gradient-to-r ${getCommitteeTypeColor(
                    committee.committee_type
                  )} rounded-xl shadow-lg group-hover:shadow-xl transition-shadow duration-300`}
                >
                  {getCommitteeTypeIcon(committee.committee_type)}
                </div>
                <h3 className="text-2xl font-bold text-gray-900 group-hover/header:text-blue-600 transition-colors duration-300">
                  {committee.name || "Unnamed Committee"}
                </h3>
              </div>
              <p className="text-gray-600 leading-relaxed line-clamp-2 text-lg">
                {committee.purpose || "No purpose provided"}
              </p>
            </div>

            <div className="flex items-center gap-4 ml-6">
              <Badge
                variant={committee.approvalStatus === "approved" ? "default" : "secondary"}
                className={`px-4 py-2 text-sm font-bold rounded-2xl shadow-lg ${committee.approvalStatus === "approved"
                  ? "bg-gradient-to-r from-green-100 to-emerald-100 text-green-800 border-green-200"
                  : committee.approvalStatus === "pending"
                    ? "bg-gradient-to-r from-yellow-100 to-amber-100 text-yellow-800 border-yellow-200"
                    : committee.approvalStatus === "rejected"
                      ? "bg-gradient-to-r from-red-100 to-rose-100 text-red-800 border-red-200"
                      : "bg-gradient-to-r from-gray-100 to-slate-100 text-gray-800 border-gray-200"
                  }`}
              >
                {committee.approvalStatus || "active"}
              </Badge>
            </div>
          </div>

          {/* Enhanced Info Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 py-6 border-t border-gray-100/80">
            <div className="flex items-center gap-4 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 rounded-2xl p-4 shadow-lg hover:shadow-xl transition-shadow duration-300 border border-blue-100/50">
              <div className="p-3 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl shadow-lg">
                <Calendar className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-xs font-bold text-blue-600 uppercase tracking-wide mb-1">Formation Date</p>
                <p className="text-sm font-bold text-gray-900">
                  {committee.formation_date ? new Date(committee.formation_date).toLocaleDateString() : "N/A"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 bg-gradient-to-r from-purple-50/80 to-pink-50/80 rounded-2xl p-4 shadow-lg hover:shadow-xl transition-shadow duration-300 border border-purple-100/50">
              <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-600 rounded-xl shadow-lg">
                <Package className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-xs font-bold text-purple-600 uppercase tracking-wide mb-1">Committee Type</p>
                <p className="text-sm font-bold text-gray-900">
                  {committee.committee_type
                    ? committee.committee_type.charAt(0).toUpperCase() + committee.committee_type.slice(1)
                    : "N/A"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 bg-gradient-to-r from-green-50/80 to-emerald-50/80 rounded-2xl p-4 shadow-lg hover:shadow-xl transition-shadow duration-300 border border-green-100/50">
              <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl shadow-lg">
                <MapPin className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-xs font-bold text-green-600 uppercase tracking-wide mb-1">Procurement Plan</p>
                <p className="text-sm font-bold text-gray-900">
                  {committee.procurement_plan ? `ID ${committee.procurement_plan}` : "None"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4 bg-gradient-to-r from-green-50/80 to-emerald-50/80 rounded-2xl p-4 shadow-lg hover:shadow-xl transition-shadow duration-300 border border-green-100/50">
              <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl shadow-lg">
                <Users className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-xs font-bold text-green-600 uppercase tracking-wide mb-1">Members</p>
                <p className="text-sm font-bold text-gray-900">
                  {Array.isArray(committee.membersList) ? committee.membersList.length : 0} Members
                </p>
              </div>
            </div>
          </div>

          {/* Committee Type Badge */}
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={`font-medium flex items-center gap-1 ${getCommitteeTypeBadgeColor(committee.committee_type)}`}
            >
              {getCommitteeTypeIcon(committee.committee_type)}
              {committee.committee_type
                ? committee.committee_type.charAt(0).toUpperCase() + committee.committee_type.slice(1)
                : "Other"}
            </Badge>

            {/* Action Hint */}
            <div className="text-sm text-gray-500 ml-auto">
              Click to{" "}
              {committee.committee_type === "specification"
                ? "view specifications"
                : committee.committee_type === "review"
                  ? "manage reviews"
                  : committee.committee_type === "evaluation"
                    ? "manage evaluations"
                    : committee.committee_type === "contract"
                      ? "manage contracts"
                      : "view details"}
            </div>
          </div>

          {/* Enhanced Members Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg">
                <Users className="h-5 w-5 text-white" />
              </div>
              <h4 className="text-lg font-bold text-gray-800">Committee Members</h4>
            </div>
            <div className="flex flex-wrap gap-3">
              {Array.isArray(committee.membersList) && committee.membersList.length > 0 ? (
                committee.membersList.map((member, index) => (
                  <Badge
                    key={`${member.employeeId}-${index}`}
                    variant="outline"
                    className="bg-gradient-to-r from-blue-50/90 to-indigo-50/90 text-blue-800 border-blue-200 hover:from-blue-100 hover:to-indigo-100 transition-all duration-300 px-4 py-2 rounded-xl shadow-md hover:shadow-lg"
                  >
                    <Users className="h-3 w-3 mr-2" />
                    {member.name} ({member.office || "Unknown"})
                  </Badge>
                ))
              ) : (
                <Badge
                  variant="outline"
                  className="bg-gradient-to-r from-gray-50 to-slate-50 text-gray-600 border-gray-200 px-4 py-2 rounded-xl"
                >
                  No members assigned
                </Badge>
              )}
            </div>
          </div>

          {/* Enhanced Formation Letter Badge */}
          {committee.formationLetterURL && (
            <div className="flex items-center gap-3 pt-4 border-t border-gray-100/80">
              <Badge className="bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-700 border-blue-200 hover:from-blue-200 hover:to-indigo-200 transition-all duration-300 px-4 py-2 rounded-xl shadow-lg">
                <Clock className="h-4 w-4 mr-2" />
                Formation Letter Available
              </Badge>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};

export default CommitteeCard;
