import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

interface CommunityPost {
  id: string;
  title: string;
  author: string;
  authorRole: string;
  content: string;
  tags: string[];
  likes: number;
  comments: number;
  time: string;
  isHot: boolean;
}

const demoPosts: CommunityPost[] = [
  {
    id: '1',
    title: '分享：如何应对客户比价',
    author: '陈明辉',
    authorRole: '资深代理人',
    content:
      '很多客户会拿其他公司的产品来比价，我的经验是不要直接否定竞品，而是帮客户建立"对比维度"。从公司实力、理赔时效、服务网点、附加服务四个维度对比，你会发现大部分客户其实更看重服务和安心感，而不只是价格。附上我的对比话术模板，希望对大家有帮助。',
    tags: ['异议处理', '比价应对', '实战分享'],
    likes: 234,
    comments: 47,
    time: '2小时前',
    isHot: true,
  },
  {
    id: '2',
    title: '新人求助：第一次电销紧张怎么办？',
    author: '林小雨',
    authorRole: '实习代理人',
    content:
      '入职第二周，明天要开始打第一批电话了，特别紧张。前辈们有什么好的心态调整方法吗？话术背了很多遍但还是怕忘词，万一客户问到我不懂的问题怎么办？求指点！',
    tags: ['新人提问', '电销技巧', '心态调整'],
    likes: 89,
    comments: 63,
    time: '5小时前',
    isHot: true,
  },
  {
    id: '3',
    title: '百万医疗险理赔案例复盘：甲状腺结节',
    author: '张伟',
    authorRole: '理赔专家',
    content:
      '最近协助一位客户完成了甲状腺结节的百万医疗险理赔，从投保前的健康告知到术后理赔，整个流程非常顺利。这个案例的亮点在于投保时我们做了充分的风险评估和健康告知指导，避免了后续纠纷。',
    tags: ['理赔案例', '百万医疗险', '健康告知'],
    likes: 178,
    comments: 32,
    time: '1天前',
    isHot: false,
  },
  {
    id: '4',
    title: '每周销售心得：从"卖保险"到"做顾问"的转变',
    author: '王芳',
    authorRole: '团队主管',
    content:
      '做保险销售三年，最大的感悟就是：不要想着"卖"保险，而是要成为客户的"风险顾问"。当你真心站在客户角度分析风险、设计方案时，成交是自然而然的结果。这个月我的转化率从12%提升到了18%。',
    tags: ['销售心得', '思维转变', '转化提升'],
    likes: 312,
    comments: 56,
    time: '2天前',
    isHot: false,
  },
  {
    id: '5',
    title: '请教：重疾险等待期内出险怎么处理？',
    author: '李婷',
    authorRole: '代理人',
    content:
      '我的一个客户在重疾险等待期内确诊了早期甲状腺癌，这种情况保险公司会怎么处理？是拒保还是等待期后重计？有没有前辈遇到过类似情况？',
    tags: ['重疾险', '等待期', '理赔问题'],
    likes: 56,
    comments: 28,
    time: '3天前',
    isHot: false,
  },
];

export function CommunityPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">AI社区</h1>
            <Badge variant="warning">演示模式</Badge>
          </div>
          <p className="text-muted text-sm mt-1">
            {user?.name || '用户'}，与同事分享经验，AI精选优秀案例和销售心得
          </p>
        </div>
        <Button variant="primary" size="sm" disabled>
          + 发布帖子
        </Button>
      </div>

      {/* Hot Tags */}
      <div className="flex gap-2 flex-wrap">
        {['🔥 热门', '异议处理', '电销技巧', '理赔案例', '新人提问', '销售心得'].map((tag) => (
          <span
            key={tag}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-card border border-border text-muted cursor-pointer hover:text-text transition-colors"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Posts */}
      <div className="space-y-3">
        {demoPosts.map((post) => (
          <Card key={post.id} padding="md" hover>
            <CardHeader>
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-full bg-accent/10 text-accent flex items-center justify-center text-sm font-bold shrink-0">
                  {post.author[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CardTitle className="text-sm">{post.title}</CardTitle>
                    {post.isHot && <Badge variant="error">热门</Badge>}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted mt-1">
                    <span className="font-medium text-text/80">{post.author}</span>
                    <span>·</span>
                    <span>{post.authorRole}</span>
                    <span>·</span>
                    <span>{post.time}</span>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardDescription className="line-clamp-2 ml-12">{post.content}</CardDescription>
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-border ml-12">
              <div className="flex gap-1.5 flex-wrap">
                {post.tags.map((tag) => (
                  <span key={tag} className="px-2 py-0.5 rounded text-xs bg-bg text-muted">
                    {tag}
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-4 text-xs text-muted shrink-0 ml-2">
                <span>👍 {post.likes}</span>
                <span>💬 {post.comments}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <p className="text-xs text-muted text-center">演示模式 — 功能待开发 · 当前展示为示例数据</p>
    </div>
  );
}
