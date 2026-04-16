import { useEffect, useState } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Alert, Chip, Table, TableBody, TableCell,
  TableHead, TableRow, Paper, Avatar, Button
} from '@mui/material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import PeopleIcon from '@mui/icons-material/People';
import WarningIcon from '@mui/icons-material/Warning';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import Layout from '../components/Layout';
import KPICard from '../components/KPICard';
import LoadingSpinner from '../components/LoadingSpinner';
import { analyticsService } from '../services/analyticsService';
import { employeeService } from '../services/employeeService';

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [empCount, setEmpCount] = useState(0);
  const [skillGaps, setSkillGaps] = useState([]);
  const [highPotentials, setHighPotentials] = useState([]);
  const [attritionRisks, setAttritionRisks] = useState([]);
  const [skillsDist, setSkillsDist] = useState([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [emps, gaps, pots, risks, dist] = await Promise.all([
          employeeService.list({ status: 'active' }),
          analyticsService.getSkillGaps(),
          analyticsService.getHighPotentials(),
          analyticsService.getAttritionRisks(),
          analyticsService.getSkillsDistribution(),
        ]);

        setEmpCount(emps.data.length);
        setSkillGaps(gaps.data);
        setHighPotentials(pots.data);
        setAttritionRisks(risks.data);
        setSkillsDist(dist.data);
      } catch (e) {
        console.error('Error loading analytics', e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <Layout><LoadingSpinner /></Layout>;

  return (
    <Layout>
      <Box className="fade-in">
        <Typography variant="h5" fontWeight={800} gutterBottom>Organizational Analytics</Typography>
        <Typography variant="body2" color="text.secondary" mb={3}>
          Data-driven insights into employee performance, skill gaps, and retention risks.
        </Typography>

        {/* Global Alert for Attrition Risks */}
        {attritionRisks.length > 0 && (
          <Alert severity="error" icon={<WarningIcon />} sx={{ mb: 4, borderRadius: 2 }}>
            <Typography fontWeight={700} gutterBottom>Action Required: Attrition Risks Identified</Typography>
            <Typography variant="body2">
              {attritionRisks.length} employee(s) have been flagged with a critical performance drop (Rating &lt; 3.0).{' '}
              Targeted retention or performance improvement plans should be initiated immediately.
            </Typography>
          </Alert>
        )}

        {/* KPI Row */}
        <Grid container spacing={3} mb={4}>
          <Grid item xs={12} sm={4}>
            <KPICard title="Total Employees" value={empCount} icon={<PeopleIcon />} color="#1565C0" subtitle="Active headcount" />
          </Grid>
          <Grid item xs={12} sm={4}>
            <KPICard title="High-Potential Stars" value={highPotentials.length} icon={<TrendingUpIcon />} color="#2E7D32" subtitle="Ready for promotion" />
          </Grid>
          <Grid item xs={12} sm={4}>
            <KPICard title="Skill Gap Incidents" value={skillGaps.length} icon={<ReportProblemIcon />} color="#E65100" subtitle="Competencies below target" />
          </Grid>
        </Grid>

        <Grid container spacing={4}>
          {/* Top High Potentials Table */}
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" fontWeight={700} gutterBottom>Top High-Potential Talent</Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>Employees exceeding expectations in both performance and goals.</Typography>
                
                <Paper elevation={0} sx={{ overflow: 'hidden', border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Employee</TableCell>
                        <TableCell>Avg Rating</TableCell>
                        <TableCell>Goal Avg</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {highPotentials.slice(0, 5).map(emp => (
                        <TableRow key={emp.employee_id} hover>
                          <TableCell>
                            <Box display="flex" alignItems="center" gap={1}>
                              <Avatar sx={{ width: 28, height: 28, fontSize: 12, bgcolor: '#2E7D32' }}>
                                {emp.employee_name?.charAt(0) || '?'}
                              </Avatar>
                              <Box>
                                <Typography variant="body2" fontWeight={600}>{emp.employee_name}</Typography>
                                <Typography variant="caption" color="text.secondary">{emp.job_title}</Typography>
                              </Box>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip label={`${emp.avg_rating.toFixed(1)}★`} size="small" color="success" sx={{ fontWeight: 700 }} />
                          </TableCell>
                          <TableCell>{emp.avg_goal_progress.toFixed(0)}%</TableCell>
                        </TableRow>
                      ))}
                      {highPotentials.length === 0 && (
                        <TableRow><TableCell colSpan={3} align="center" sx={{ py: 3, color: 'text.secondary' }}>No high potentials identified yet.</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </Paper>
              </CardContent>
            </Card>
          </Grid>

          {/* Skill Distribution Chart */}
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" fontWeight={700} gutterBottom>Organizational Skill Levels</Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>Average competency level across the organization.</Typography>
                
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={skillsDist} layout="vertical" margin={{ left: 60, right: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" domain={[0, 5]} ticks={[1, 2, 3, 4, 5]} />
                    <YAxis type="category" dataKey="competency_name" tick={{ fontSize: 11 }} width={100} />
                    <Tooltip cursor={{ fill: 'rgba(0,0,0,0.05)' }} formatter={(val) => [val.toFixed(1), 'Avg Level']} />
                    <Bar dataKey="avg_level" fill="#1565C0" radius={[0, 4, 4, 0]} barSize={15} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>

          {/* Skill Gaps List */}
          <Grid item xs={12}>
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" fontWeight={700} gutterBottom>Critical Skill Gaps Tracking</Typography>
                <Paper elevation={0} sx={{ overflow: 'hidden', border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Employee Name</TableCell>
                        <TableCell>Department</TableCell>
                        <TableCell>Required Competency</TableCell>
                        <TableCell>Target Level</TableCell>
                        <TableCell>Current Level</TableCell>
                        <TableCell>Gap</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {skillGaps.map((gap, i) => (
                        <TableRow key={i} hover>
                          <TableCell fontWeight={500}>{gap.employee_name}</TableCell>
                          <TableCell>{gap.department}</TableCell>
                          <TableCell>{gap.competency}</TableCell>
                          <TableCell>{gap.target_level}</TableCell>
                          <TableCell>{gap.current_level}</TableCell>
                          <TableCell>
                            <Chip label={`-${gap.target_level - gap.current_level}`} size="small" color="warning" sx={{ fontWeight: 700 }} />
                          </TableCell>
                        </TableRow>
                      ))}
                      {skillGaps.length === 0 && (
                        <TableRow><TableCell colSpan={6} align="center" sx={{ py: 3, color: 'text.secondary' }}>No critical skill gaps identified.</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </Paper>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Layout>
  );
}
